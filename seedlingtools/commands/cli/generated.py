from __future__ import annotations
import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Sequence, Tuple, Callable

from .base import AbstractPluginCommand
from .registry import AbstractCommandRegistry
from ...utils import ConfigurationError, FileSystemError, PluginLoadError


GENERATED_TOOLS_DIR_NAME: Final[str] = ".seedling"
GENERATED_TOOLS_FILE_NAME: Final[str] = "commands.json"
RESERVED_COMMAND_NAMES: Final[Tuple[str, ...]] = (
    "scan",
    "build",
    "clean",
    "config",
    "tools"
)
SAFE_SHELL_TOKENS: Final[Tuple[str, ...]] = ("&&", "||", ";", "|", "`", "$(", ">", "<")


@dataclass(frozen=True)
class ToolArgumentSpec:
    name: str
    required: bool = False
    flag: Optional[str] = None
    default: Optional[str] = None


@dataclass(frozen=True)
class GeneratedCommandSpec:
    name: str
    description: str
    type: str
    command: Optional[str] = None
    args: Tuple[ToolArgumentSpec, ...] = ()
    method: Optional[str] = None
    url: Optional[str] = None
    headers_env: Tuple[str, ...] = ()
    body_template: Optional[Dict[str, Any]] = None


class GeneratedToolCommand(AbstractPluginCommand):
    def __init__(self, spec: GeneratedCommandSpec) -> None:
        self._spec: Final[GeneratedCommandSpec] = spec

    @property
    def command_name(self) -> str:
        return self._spec.name

    @property
    def description(self) -> str:
        return self._spec.description

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        for arg in self._spec.args:
            if arg.flag is None:
                parser.add_argument(arg.name)
            else:
                parser.add_argument(arg.flag, dest=arg.name, default=arg.default, required=arg.required)

    def execute(self, args: argparse.Namespace) -> None:
        if self._spec.type == "shell":
            _execute_shell_tool(self._spec, args)
            return
        if self._spec.type == "api":
            _execute_api_tool(self._spec, args)
            return
        raise ConfigurationError(
            message=f"Unsupported generated tool type: {self._spec.type}",
            context={"command": self._spec.name}
        )


class GeneratedToolsManager:
    def __init__(self, cwd: Path) -> None:
        self._cwd: Final[Path] = cwd.resolve(strict=False)
        self._seedling_dir: Final[Path] = self._cwd / GENERATED_TOOLS_DIR_NAME
        self._spec_path: Final[Path] = self._seedling_dir / GENERATED_TOOLS_FILE_NAME

    @property
    def spec_path(self) -> Path:
        return self._spec_path

    def load_specs(self) -> List[GeneratedCommandSpec]:
        if self._spec_path.exists() is False:
            return []

        try:
            payload: Any = json.loads(self._spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise ConfigurationError(
                message=f"Malformed generated tools spec: {self._spec_path}",
                context={"path": str(self._spec_path), "error": str(err)}
            ) from err
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to read generated tools spec: {self._spec_path.name}",
                context={"path": str(self._spec_path)}
            ) from err

        return _parse_generated_specs(payload, self._spec_path)

    def save_specs(self, specs: Sequence[GeneratedCommandSpec]) -> None:
        payload: Dict[str, Any] = {
            "commands": [_spec_to_json(spec) for spec in specs]
        }
        try:
            if self._seedling_dir.exists() is False:
                self._seedling_dir.mkdir(parents=True, exist_ok=True)
            self._spec_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to write generated tools spec: {self._spec_path.name}",
                context={"path": str(self._spec_path)}
            ) from err

    def register_into(self, registry: AbstractCommandRegistry) -> None:
        for spec in self.load_specs():
            registry.register_command(GeneratedToolCommand(spec), is_builtin=False)

    def add_spec_from_file(self, spec_file: Path) -> GeneratedCommandSpec:
        try:
            payload: Any = json.loads(spec_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise ConfigurationError(
                message=f"Malformed tool spec file: {spec_file}",
                context={"path": str(spec_file), "error": str(err)}
            ) from err
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to read tool spec file: {spec_file.name}",
                context={"path": str(spec_file)}
            ) from err

        parsed_specs: List[GeneratedCommandSpec] = _parse_generated_specs(payload, spec_file)
        if len(parsed_specs) != 1:
            raise ConfigurationError(
                message=f"Tool spec file must contain exactly one command: {spec_file}",
                context={"path": str(spec_file)}
            )

        existing_specs: List[GeneratedCommandSpec] = self.load_specs()
        new_spec: GeneratedCommandSpec = parsed_specs[0]
        for existing in existing_specs:
            if existing.name == new_spec.name:
                raise ConfigurationError(
                    message=f"Generated tool already exists: {new_spec.name}",
                    context={"command": new_spec.name}
                )
        existing_specs.append(new_spec)
        self.save_specs(existing_specs)
        return new_spec

    def remove_spec(self, command_name: str) -> bool:
        specs: List[GeneratedCommandSpec] = self.load_specs()
        filtered: List[GeneratedCommandSpec] = []
        removed: bool = False
        for spec in specs:
            if spec.name == command_name:
                removed = True
                continue
            filtered.append(spec)
        if removed is True:
            self.save_specs(filtered)
        return removed


class ToolsCommand(AbstractPluginCommand):
    def __init__(self, cwd_provider: Optional[Callable[[], Path]] = None) -> None:
        self._cwd_provider = cwd_provider

    @property
    def command_name(self) -> str:
        return "tools"

    @property
    def description(self) -> str:
        return "Manage generated Seedling tools"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="tools_action")

        list_parser = subparsers.add_parser("list", help="List generated tools")
        list_parser.set_defaults(tools_handler=self._list)

        add_parser = subparsers.add_parser("add", help="Add a generated tool from a spec file")
        add_parser.add_argument("spec_file")
        add_parser.set_defaults(tools_handler=self._add)

        remove_parser = subparsers.add_parser("remove", help="Remove a generated tool by name")
        remove_parser.add_argument("name")
        remove_parser.set_defaults(tools_handler=self._remove)

        validate_parser = subparsers.add_parser("validate", help="Validate generated tool specs")
        validate_parser.set_defaults(tools_handler=self._validate)

        export_parser = subparsers.add_parser("export", help="Print generated tool specs")
        export_parser.set_defaults(tools_handler=self._export)

    def execute(self, args: argparse.Namespace) -> None:
        if hasattr(args, "tools_handler") is False:
            raise ConfigurationError(
                message="Missing tools subcommand.",
                hint="Use one of: list, add, remove, validate, export."
            )
        handler = getattr(args, "tools_handler")
        handler(args)

    def _list(self, args: argparse.Namespace) -> None:
        manager = GeneratedToolsManager(_resolve_tools_cwd(self._cwd_provider))
        specs = manager.load_specs()
        print(json.dumps({"commands": [_spec_to_json(spec) for spec in specs]}, ensure_ascii=False, indent=2, sort_keys=True))

    def _add(self, args: argparse.Namespace) -> None:
        manager = GeneratedToolsManager(_resolve_tools_cwd(self._cwd_provider))
        spec = manager.add_spec_from_file(Path(args.spec_file).resolve(strict=False))
        print(json.dumps(_spec_to_json(spec), ensure_ascii=False, indent=2, sort_keys=True))

    def _remove(self, args: argparse.Namespace) -> None:
        manager = GeneratedToolsManager(_resolve_tools_cwd(self._cwd_provider))
        removed = manager.remove_spec(args.name)
        if removed is False:
            raise ConfigurationError(
                message=f"Generated tool not found: {args.name}",
                context={"command": args.name}
            )
        print(json.dumps({"removed": args.name}, ensure_ascii=False, indent=2, sort_keys=True))

    def _validate(self, args: argparse.Namespace) -> None:
        manager = GeneratedToolsManager(_resolve_tools_cwd(self._cwd_provider))
        specs = manager.load_specs()
        print(json.dumps({"valid": True, "commands": [spec.name for spec in specs]}, ensure_ascii=False, indent=2, sort_keys=True))

    def _export(self, args: argparse.Namespace) -> None:
        manager = GeneratedToolsManager(_resolve_tools_cwd(self._cwd_provider))
        specs = manager.load_specs()
        print(json.dumps({"commands": [_spec_to_json(spec) for spec in specs]}, ensure_ascii=False, indent=2, sort_keys=True))


def register_generated_tools(cwd: Path, registry: AbstractCommandRegistry) -> None:
    manager = GeneratedToolsManager(cwd)
    manager.register_into(registry)


def _resolve_tools_cwd(cwd_provider: Optional[Callable[[], Path]] = None) -> Path:
    if cwd_provider is not None:
        return cwd_provider().resolve(strict=False)
    return Path.cwd().resolve(strict=False)


def _parse_generated_specs(payload: Any, source_path: Path) -> List[GeneratedCommandSpec]:
    if isinstance(payload, dict) is False:
        raise ConfigurationError(
            message=f"Generated tools spec must be a JSON object: {source_path}",
            context={"path": str(source_path)}
        )

    raw_commands: Any = payload.get("commands")
    if isinstance(raw_commands, list) is False:
        raise ConfigurationError(
            message=f"Generated tools spec must contain a 'commands' list: {source_path}",
            context={"path": str(source_path)}
        )

    parsed_specs: List[GeneratedCommandSpec] = []
    seen_names: set[str] = set()
    for raw_command in raw_commands:
        spec = _parse_generated_spec(raw_command, source_path)
        if spec.name in seen_names:
            raise ConfigurationError(
                message=f"Duplicate generated tool name: {spec.name}",
                context={"path": str(source_path), "command": spec.name}
            )
        seen_names.add(spec.name)
        parsed_specs.append(spec)
    return parsed_specs


def _parse_generated_spec(raw_command: Any, source_path: Path) -> GeneratedCommandSpec:
    if isinstance(raw_command, dict) is False:
        raise ConfigurationError(
            message=f"Generated tool entries must be objects: {source_path}",
            context={"path": str(source_path)}
        )

    name = str(raw_command.get("name", "")).strip()
    description = str(raw_command.get("description", "")).strip()
    command_type = str(raw_command.get("type", "")).strip().lower()

    if len(name) == 0:
        raise ConfigurationError(message=f"Generated tool is missing a name: {source_path}", context={"path": str(source_path)})
    if name in RESERVED_COMMAND_NAMES:
        raise ConfigurationError(message=f"Generated tool cannot override builtin command: {name}", context={"command": name})
    if len(description) == 0:
        raise ConfigurationError(message=f"Generated tool is missing a description: {name}", context={"command": name})
    if command_type not in ("shell", "api"):
        raise ConfigurationError(message=f"Generated tool has unsupported type: {command_type}", context={"command": name})

    args = _parse_argument_specs(raw_command.get("args", []), source_path, name)

    if command_type == "shell":
        command = str(raw_command.get("command", "")).strip()
        if len(command) == 0:
            raise ConfigurationError(message=f"Shell tool is missing command string: {name}", context={"command": name})
        _validate_shell_command(command, name)
        return GeneratedCommandSpec(name=name, description=description, type=command_type, command=command, args=args)

    method = str(raw_command.get("method", "")).strip().upper()
    url = str(raw_command.get("url", "")).strip()
    headers_env = raw_command.get("headers_env", [])
    body_template = raw_command.get("body_template", None)

    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        raise ConfigurationError(message=f"API tool has unsupported method: {name}", context={"command": name})
    if len(url) == 0:
        raise ConfigurationError(message=f"API tool is missing URL: {name}", context={"command": name})
    if isinstance(headers_env, list) is False:
        raise ConfigurationError(message=f"API tool headers_env must be a list: {name}", context={"command": name})
    for env_key in headers_env:
        if isinstance(env_key, str) is False or len(env_key.strip()) == 0:
            raise ConfigurationError(message=f"API tool headers_env entries must be strings: {name}", context={"command": name})
    if body_template is not None and isinstance(body_template, dict) is False:
        raise ConfigurationError(message=f"API tool body_template must be an object: {name}", context={"command": name})

    return GeneratedCommandSpec(
        name=name,
        description=description,
        type=command_type,
        args=args,
        method=method,
        url=url,
        headers_env=tuple(str(item) for item in headers_env),
        body_template=body_template
    )


def _parse_argument_specs(raw_args: Any, source_path: Path, command_name: str) -> Tuple[ToolArgumentSpec, ...]:
    if raw_args is None:
        return ()
    if isinstance(raw_args, list) is False:
        raise ConfigurationError(
            message=f"Generated tool args must be a list: {command_name}",
            context={"path": str(source_path), "command": command_name}
        )

    specs: List[ToolArgumentSpec] = []
    for raw_arg in raw_args:
        if isinstance(raw_arg, dict) is False:
            raise ConfigurationError(
                message=f"Generated tool arg entries must be objects: {command_name}",
                context={"path": str(source_path), "command": command_name}
            )
        arg_name = str(raw_arg.get("name", "")).strip()
        if len(arg_name) == 0:
            raise ConfigurationError(message=f"Generated tool arg is missing name: {command_name}", context={"command": command_name})
        required = bool(raw_arg.get("required", False))
        flag_value = raw_arg.get("flag")
        flag = None if flag_value is None else str(flag_value)
        default_value = raw_arg.get("default")
        default = None if default_value is None else str(default_value)
        specs.append(ToolArgumentSpec(name=arg_name, required=required, flag=flag, default=default))
    return tuple(specs)


def _validate_shell_command(command: str, command_name: str) -> None:
    for token in SAFE_SHELL_TOKENS:
        if token in command:
            raise ConfigurationError(
                message=f"Shell tool contains unsafe token '{token}': {command_name}",
                hint="Use a simple command template without shell operators.",
                context={"command": command_name}
            )


def _render_shell_command(spec: GeneratedCommandSpec, args: argparse.Namespace) -> List[str]:
    if spec.command is None:
        raise ConfigurationError(message=f"Shell tool has no command template: {spec.name}", context={"command": spec.name})

    values: Dict[str, str] = {}
    for arg in spec.args:
        value = getattr(args, arg.name, None)
        if value is None:
            if arg.default is not None:
                value = arg.default
            elif arg.required is True:
                raise ConfigurationError(message=f"Missing required argument: {arg.name}", context={"command": spec.name})
            else:
                value = ""
        values[arg.name] = str(value)

    rendered = spec.command.format(**values)
    return shlex.split(rendered)


def _execute_shell_tool(spec: GeneratedCommandSpec, args: argparse.Namespace) -> None:
    command = _render_shell_command(spec, args)
    try:
        completed = subprocess.run(command, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as err:
        raise ConfigurationError(
            message=f"Generated shell tool failed: {spec.name}",
            context={"command": spec.name, "stderr": err.stderr.strip()}
        ) from err
    if len(completed.stdout) > 0:
        print(completed.stdout.rstrip())


def _execute_api_tool(spec: GeneratedCommandSpec, args: argparse.Namespace) -> None:
    if spec.url is None or spec.method is None:
        raise ConfigurationError(message=f"API tool is incomplete: {spec.name}", context={"command": spec.name})

    values: Dict[str, str] = {}
    for arg in spec.args:
        raw_value = getattr(args, arg.name, None)
        if raw_value is None:
            if arg.default is not None:
                raw_value = arg.default
            elif arg.required is True:
                raise ConfigurationError(message=f"Missing required argument: {arg.name}", context={"command": spec.name})
            else:
                raw_value = ""
        values[arg.name] = str(raw_value)

    payload: Dict[str, Any] = {}
    if spec.body_template is not None:
        payload = _render_json_template(spec.body_template, values)

    headers: Dict[str, str] = {}
    for env_key in spec.headers_env:
        env_value = os.environ.get(env_key)
        if env_value is None:
            raise ConfigurationError(
                message=f"Required environment variable is missing for API tool: {env_key}",
                context={"command": spec.name, "env": env_key}
            )
        headers[env_key] = env_value

    print(json.dumps({
        "command": spec.name,
        "method": spec.method,
        "url": spec.url.format(**values),
        "headers_env": list(spec.headers_env),
        "body": payload
    }, ensure_ascii=False, indent=2, sort_keys=True))


def _render_json_template(payload: Dict[str, Any], values: Dict[str, str]) -> Dict[str, Any]:
    rendered: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str) is True:
            rendered[key] = value.format(**values)
        else:
            rendered[key] = value
    return rendered


def _spec_to_json(spec: GeneratedCommandSpec) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "name": spec.name,
        "description": spec.description,
        "type": spec.type,
    }
    if spec.command is not None:
        payload["command"] = spec.command
    if len(spec.args) > 0:
        payload["args"] = [
            {
                "name": arg.name,
                "required": arg.required,
                **({"flag": arg.flag} if arg.flag is not None else {}),
                **({"default": arg.default} if arg.default is not None else {}),
            }
            for arg in spec.args
        ]
    if spec.method is not None:
        payload["method"] = spec.method
    if spec.url is not None:
        payload["url"] = spec.url
    if len(spec.headers_env) > 0:
        payload["headers_env"] = list(spec.headers_env)
    if spec.body_template is not None:
        payload["body_template"] = spec.body_template
    return payload
