from __future__ import annotations
import argparse
import atexit
import json
from pathlib import Path
from typing import Any, Dict, Final, Tuple

from .base import AbstractPluginCommand
from .generated import ToolsCommand
from ..scan import setup_scan_parser, handle_scan
from ..build import setup_build_parser, handle_build
from ..clean import setup_clean_parser, handle_clean
from ...core import CommentStripper, config_manager
from ...utils import ConfigurationError, io_processor, gitter


ALLOWED_PREFERENCE_KEYS: Final[Tuple[str, ...]] = (
    "output_format",
    "common_excludes",
    "default_scan_depth",
    "show_hidden",
    "build_output_dir",
    "clean_strategy"
)


class ScanCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "scan"

    @property
    def description(self) -> str:
        return "Directory explorer and context exporter"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        setup_scan_parser(parser)

    def execute(self, args: argparse.Namespace) -> None:
        if _is_remote_url(args.target) is True:
            repo_path: Path = gitter.clone_repository(args.target)
            atexit.register(gitter.cleanup_repository, repo_path)
            args.target = str(repo_path)

        scan_cwd: Path = Path(args.target).resolve(strict=False)
        config_manager.initialize(cwd=scan_cwd)
        handle_scan(args)


class BuildCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "build"

    @property
    def description(self) -> str:
        return "Project structure builder"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        setup_build_parser(parser)

    def execute(self, args: argparse.Namespace) -> None:
        handle_build(args)


class CleanCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "clean"

    @property
    def description(self) -> str:
        return "Smart cache sweeper"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        setup_clean_parser(parser)

    def execute(self, args: argparse.Namespace) -> None:
        handle_clean(args)


class StripCommentsCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "strip-comments"

    @property
    def description(self) -> str:
        return "Strip comments from a source file"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Source file to process")
        parser.add_argument("--out", dest="out_file", default=None, help="Write stripped content to a new file")
        parser.add_argument("--in-place", action="store_true", dest="in_place", help="Overwrite the source file in place")
        parser.add_argument("--check", action="store_true", help="Preview stripping and token savings without writing")

    def execute(self, args: argparse.Namespace) -> None:
        source_path: Path = Path(args.path).resolve(strict=False)
        if source_path.exists() is False or source_path.is_file() is False:
            raise ConfigurationError(
                message=f"Target file does not exist: {args.path}",
                hint="Provide a readable source file path."
            )
        if args.in_place is True and args.out_file is not None:
            raise ConfigurationError(
                message="Cannot combine --in-place with --out.",
                hint="Choose one output mode."
            )

        stripper = CommentStripper()
        result = stripper.strip_file(source_path)

        if args.check is True:
            print(json.dumps({
                "path": str(source_path),
                "baseline_tokens": result.original_tokens,
                "stripped_tokens": result.stripped_tokens,
                "saved_tokens": result.saved_tokens,
                "saved_percent": round(result.saved_percent, 2)
            }, ensure_ascii=False, indent=2, sort_keys=True))
            return

        if args.in_place is True:
            io_processor.write_text_safely(source_path, result.stripped_text)
            print(json.dumps({
                "path": str(source_path),
                "mode": "in-place",
                "saved_tokens": result.saved_tokens,
                "saved_percent": round(result.saved_percent, 2)
            }, ensure_ascii=False, indent=2, sort_keys=True))
            return

        out_file = Path(args.out_file).resolve(strict=False) if args.out_file is not None else Path.cwd() / f"{source_path.stem}_stripped{source_path.suffix}"
        io_processor.write_text_safely(out_file, result.stripped_text)
        print(json.dumps({
            "path": str(source_path),
            "output": str(out_file),
            "mode": "copy",
            "saved_tokens": result.saved_tokens,
            "saved_percent": round(result.saved_percent, 2)
        }, ensure_ascii=False, indent=2, sort_keys=True))


class ConfigCommand(AbstractPluginCommand):
    @property
    def command_name(self) -> str:
        return "config"

    @property
    def description(self) -> str:
        return "Show and manage Seedling preferences"

    def setup_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="config_action")

        show_parser = subparsers.add_parser("show", help="Show effective preferences")
        show_parser.set_defaults(config_handler=self._show)

        set_parser = subparsers.add_parser("set", help="Set a preference key")
        set_parser.add_argument("key", choices=list(ALLOWED_PREFERENCE_KEYS))
        set_parser.add_argument("value")
        set_parser.set_defaults(config_handler=self._set)

        unset_parser = subparsers.add_parser("unset", help="Unset a preference key")
        unset_parser.add_argument("key", choices=list(ALLOWED_PREFERENCE_KEYS))
        unset_parser.set_defaults(config_handler=self._unset)

        reset_parser = subparsers.add_parser("reset", help="Reset preferences to defaults")
        reset_parser.set_defaults(config_handler=self._reset)

    def execute(self, args: argparse.Namespace) -> None:
        if hasattr(args, "config_handler") is False:
            raise ConfigurationError(
                message="Missing config subcommand.",
                hint="Use one of: show, set, unset, reset."
            )

        handler = getattr(args, "config_handler")
        handler(args)

    def _show(self, args: argparse.Namespace) -> None:
        preferences: Dict[str, Any] = config_manager.build_preferences_config(args)
        print(json.dumps(preferences, ensure_ascii=False, indent=2, sort_keys=True))

    def _set(self, args: argparse.Namespace) -> None:
        key: str = args.key
        value: Any = _parse_preference_value(key, args.value)
        config_manager.update_preference(key, value)
        config_manager.save()
        preferences: Dict[str, Any] = config_manager.build_preferences_config(args)
        print(json.dumps(preferences, ensure_ascii=False, indent=2, sort_keys=True))

    def _unset(self, args: argparse.Namespace) -> None:
        config_manager.update_preference(args.key, None)
        config_manager.save()
        preferences: Dict[str, Any] = config_manager.build_preferences_config(args)
        print(json.dumps(preferences, ensure_ascii=False, indent=2, sort_keys=True))

    def _reset(self, args: argparse.Namespace) -> None:
        config_manager.reset_preferences()
        config_manager.save()
        preferences: Dict[str, Any] = config_manager.build_preferences_config(args)
        print(json.dumps(preferences, ensure_ascii=False, indent=2, sort_keys=True))


BUILTIN_COMMANDS: Final[Tuple[AbstractPluginCommand, ...]] = (
    ScanCommand(),
    BuildCommand(),
    CleanCommand(),
    ConfigCommand(),
    StripCommentsCommand(),
    ToolsCommand()
)


def _is_remote_url(target: str) -> bool:
    if target.startswith("http://") is True:
        return True
    elif target.startswith("https://") is True:
        return True
    elif target.startswith("git@") is True:
        return True
    else:
        return False


def _parse_preference_value(key: str, raw_value: str) -> Any:
    if key == "default_scan_depth":
        try:
            return int(raw_value)
        except ValueError as err:
            raise ConfigurationError(
                message=f"Preference '{key}' requires an integer value.",
                hint="Provide a whole number such as 2 or 5."
            ) from err

    if key == "show_hidden":
        normalized: str = raw_value.strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off"):
            return False
        raise ConfigurationError(
            message=f"Preference '{key}' requires a boolean value.",
            hint="Use true/false."
        )

    if key == "common_excludes":
        parts = [item.strip() for item in raw_value.split(",") if len(item.strip()) > 0]
        return parts

    return raw_value
