from __future__ import annotations
import argparse
import copy
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Tuple

from .config import BuildConfig, CleanConfig, ScanConfig
from ..utils import (
    ConfigurationCorruptionError,
    ConfigurationLoadError,
    ConfigurationWriteError,
    logger,
    SingletonMeta
)


DEFAULT_CONFIG: Final[Dict[str, Any]] = {
    "schema_version": 1,
    "scan": {
        "max_depth": None,
        "show_hidden": True,
        "excludes": [],
        "includes": [],
        "text_only": False,
        "file_type": None,
        "quiet": False,
        "use_regex": False,
        "ignore_case": False,
        "template_path": None,
        "strip_comments": False
    },
    "build": {
        "default_target": None,
        "force": False,
        "check": False,
        "direct": False,
        "allow_overwrite": False
    },
    "clean": {
        "strategy": "python-standard",
        "dry_run_default": False,
        "recursive_dirs": [
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".tox",
            ".nox"
        ],
        "root_only_dirs": ["build", "dist"],
        "extensions": [".pyc", ".pyo", ".pyd"],
        "ignore_dirs": [".git", ".venv", "venv", "env", ".env", "node_modules"],
        "custom_targets": [],
        "external_script": None,
        "external_mode": "candidates-only"
    },
    "preferences": {
        "output_format": None,
        "common_excludes": [],
        "default_scan_depth": None,
        "show_hidden": None,
        "build_output_dir": None,
        "clean_strategy": None
    },
    "commands": {
        "plugin_dirs": ["~/.seedling/plugins"],
        "autoload": True,
        "strict": False
    },
    "state": {}
}


class AbstractConfigManager(ABC):
    @abstractmethod
    def initialize(self, cwd: Optional[Path] = None, quiet_init: bool = False) -> None:
        pass

    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def build_scan_config(self, args: argparse.Namespace) -> ScanConfig:
        pass

    @abstractmethod
    def build_build_config(self, args: argparse.Namespace) -> BuildConfig:
        pass

    @abstractmethod
    def build_clean_config(self, args: argparse.Namespace) -> CleanConfig:
        pass

    @abstractmethod
    def build_preferences_config(self, args: argparse.Namespace) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_preference(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def reset_preferences(self) -> None:
        pass

    @abstractmethod
    def update_state(self, key: str, value: Any) -> None:
        pass

    @abstractmethod
    def save(self) -> None:
        pass


class SeedlingConfigManager(AbstractConfigManager, metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.global_config_path: Path = Path.home() / ".seedling" / "config.json"
        self.local_config_path: Optional[Path] = None
        self._global_config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._merged_config: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._initialized: bool = False
        self._cwd: Path = Path.cwd().resolve(strict=False)

    def initialize(self, cwd: Optional[Path] = None, quiet_init: bool = False) -> None:
        self.global_config_path = Path.home() / ".seedling" / "config.json"
        self._ensure_global_config_exists(quiet_init=quiet_init)

        global_config: Dict[str, Any] = self._load_config_file(self.global_config_path)
        merged_config: Dict[str, Any] = self._merge_config(copy.deepcopy(DEFAULT_CONFIG), global_config)

        current_dir: Path = Path.cwd().resolve(strict=False)
        if cwd is not None:
            current_dir = cwd.resolve(strict=False)

        self._cwd = current_dir
        self.local_config_path = current_dir / ".seedling.json"
        if self.local_config_path.exists() is True:
            local_config: Dict[str, Any] = self._load_config_file(self.local_config_path)
            merged_config = self._merge_config(merged_config, local_config)

        self._validate_config_shape(merged_config, self.global_config_path)
        self._global_config = self._merge_config(copy.deepcopy(DEFAULT_CONFIG), global_config)
        self._merged_config = merged_config
        self._initialized = True

    def get_section(self, section: str) -> Dict[str, Any]:
        self._ensure_initialized()
        value: Any = self._merged_config.get(section, {})
        if isinstance(value, dict) is False:
            raise ConfigurationCorruptionError(
                message=f"Configuration section '{section}' must be an object.",
                context={"section": section}
            )
        return copy.deepcopy(value)

    def build_scan_config(self, args: argparse.Namespace) -> ScanConfig:
        self._ensure_initialized()
        scan_section: Dict[str, Any] = self.get_section("scan")

        max_depth: Optional[int] = scan_section["max_depth"]
        if hasattr(args, "depth") is True:
            if getattr(args, "depth") is not None:
                max_depth = getattr(args, "depth")

        show_hidden: bool = bool(scan_section["show_hidden"])
        if hasattr(args, "no_hidden") is True:
            if getattr(args, "no_hidden") is True:
                show_hidden = False

        excludes: List[str] = []
        for item in scan_section["excludes"]:
            excludes.append(str(item))
        if hasattr(args, "exclude") is True:
            if getattr(args, "exclude") is not None:
                excludes = []
                for item in getattr(args, "exclude"):
                    excludes.append(str(item))

        includes: List[str] = []
        for item in scan_section["includes"]:
            includes.append(str(item))
        if hasattr(args, "include") is True:
            if getattr(args, "include") is not None:
                includes = []
                for item in getattr(args, "include"):
                    includes.append(str(item))

        text_only: bool = bool(scan_section["text_only"])
        if hasattr(args, "text_only") is True:
            if getattr(args, "text_only") is True:
                text_only = True

        file_type: Optional[str] = scan_section["file_type"]
        if hasattr(args, "type") is True:
            if getattr(args, "type") is not None:
                file_type = getattr(args, "type")

        quiet: bool = bool(scan_section["quiet"])
        if hasattr(args, "quiet") is True:
            if getattr(args, "quiet") is True:
                quiet = True

        use_regex: bool = bool(scan_section["use_regex"])
        if hasattr(args, "regex") is True:
            if getattr(args, "regex") is True:
                use_regex = True

        ignore_case: bool = bool(scan_section["ignore_case"])
        if hasattr(args, "ignore_case") is True:
            if getattr(args, "ignore_case") is True:
                ignore_case = True

        template_path: Optional[Path] = None
        template_value: Optional[str] = scan_section["template_path"]
        if template_value is not None:
            template_path = Path(str(template_value)).expanduser().resolve(strict=False)
        if hasattr(args, "template") is True:
            if getattr(args, "template") is not None:
                template_path = Path(getattr(args, "template")).resolve(strict=False)

        strip_comments: bool = bool(scan_section["strip_comments"])
        if hasattr(args, "strip_comments") is True:
            if getattr(args, "strip_comments") is True:
                strip_comments = True

        return ScanConfig(
            max_depth=max_depth,
            show_hidden=show_hidden,
            excludes=excludes,
            includes=includes,
            text_only=text_only,
            file_type=file_type,
            quiet=quiet,
            use_regex=use_regex,
            ignore_case=ignore_case,
            template_path=template_path,
            strip_comments=strip_comments
        )

    def build_build_config(self, args: argparse.Namespace) -> BuildConfig:
        self._ensure_initialized()
        build_section: Dict[str, Any] = self.get_section("build")

        default_target: Optional[Path] = None
        default_target_value: Any = build_section["default_target"]
        if default_target_value is not None:
            default_target = self._resolve_config_path(str(default_target_value))

        if hasattr(args, "target") is True:
            if getattr(args, "target") is not None:
                default_target = self._resolve_config_path(str(getattr(args, "target")))

        force: bool = bool(build_section["force"])
        if hasattr(args, "force") is True:
            if getattr(args, "force") is True:
                force = True

        check: bool = bool(build_section["check"])
        if hasattr(args, "check") is True:
            if getattr(args, "check") is True:
                check = True

        direct: bool = bool(build_section["direct"])
        if hasattr(args, "direct") is True:
            if getattr(args, "direct") is True:
                direct = True

        allow_overwrite: bool = bool(build_section["allow_overwrite"])
        if force is True:
            allow_overwrite = True
        if hasattr(args, "force") is True:
            if getattr(args, "force") is True:
                allow_overwrite = True

        return BuildConfig(
            default_target=default_target,
            force=force,
            check=check,
            direct=direct,
            allow_overwrite=allow_overwrite
        )

    def build_clean_config(self, args: argparse.Namespace) -> CleanConfig:
        self._ensure_initialized()
        clean_section: Dict[str, Any] = self.get_section("clean")

        strategy: str = str(clean_section["strategy"]).strip().lower()
        if len(strategy) == 0:
            strategy = "python-standard"
        if hasattr(args, "strategy") is True:
            if getattr(args, "strategy") is not None:
                strategy = str(getattr(args, "strategy")).strip().lower()

        dry_run_default: bool = bool(clean_section["dry_run_default"])
        if hasattr(args, "dry_run") is True:
            if getattr(args, "dry_run") is True:
                dry_run_default = True
            elif getattr(args, "dry_run") is False:
                dry_run_default = False

        recursive_dirs: List[str] = []
        for item in clean_section["recursive_dirs"]:
            recursive_dirs.append(str(item))

        root_only_dirs: List[str] = []
        for item in clean_section["root_only_dirs"]:
            root_only_dirs.append(str(item))

        extensions: List[str] = []
        for item in clean_section["extensions"]:
            extensions.append(str(item))

        ignore_dirs: List[str] = []
        for item in clean_section["ignore_dirs"]:
            ignore_dirs.append(str(item))

        custom_targets: List[str] = []
        for item in clean_section["custom_targets"]:
            custom_targets.append(str(item))

        external_script: Optional[Path] = None
        external_script_value: Any = clean_section["external_script"]
        if external_script_value is not None:
            external_script = self._resolve_config_path(str(external_script_value))

        external_mode: str = str(clean_section["external_mode"]).strip().lower()
        if len(external_mode) == 0:
            external_mode = "candidates-only"

        return CleanConfig(
            strategy=strategy,
            dry_run_default=dry_run_default,
            recursive_dirs=recursive_dirs,
            root_only_dirs=root_only_dirs,
            extensions=extensions,
            ignore_dirs=ignore_dirs,
            custom_targets=custom_targets,
            external_script=external_script,
            external_mode=external_mode
        )

    def build_preferences_config(self, args: argparse.Namespace) -> Dict[str, Any]:
        self._ensure_initialized()
        preferences_section: Dict[str, Any] = self.get_section("preferences")
        return self._merge_config(copy.deepcopy(DEFAULT_CONFIG["preferences"]), preferences_section)

    def update_preference(self, key: str, value: Any) -> None:
        self._ensure_initialized()
        preferences: Dict[str, Any] = self._global_config.setdefault("preferences", {})
        if value is None:
            preferences.pop(key, None)
        else:
            preferences[key] = value
        self._merged_config["preferences"] = self._merge_config(copy.deepcopy(DEFAULT_CONFIG["preferences"]), preferences)

    def reset_preferences(self) -> None:
        self._ensure_initialized()
        self._global_config["preferences"] = copy.deepcopy(DEFAULT_CONFIG["preferences"])
        self._merged_config["preferences"] = copy.deepcopy(DEFAULT_CONFIG["preferences"])

    def update_state(self, key: str, value: Any) -> None:
        self._ensure_initialized()
        state: Dict[str, Any] = self._global_config["state"]
        state[key] = value
        self._merged_config["state"] = copy.deepcopy(state)

    def save(self) -> None:
        if self._initialized is False:
            return

        try:
            parent_dir: Path = self.global_config_path.parent
            if parent_dir.exists() is False:
                parent_dir.mkdir(parents=True, exist_ok=True)
            with open(self.global_config_path, "w", encoding="utf-8") as file_obj:
                json.dump(self._global_config, file_obj, ensure_ascii=False, indent=2, sort_keys=True)
                file_obj.write("\n")
        except OSError as err:
            raise ConfigurationWriteError(
                message=f"Failed to write Seedling configuration: {self.global_config_path}",
                context={"path": str(self.global_config_path)}
            ) from err

    def _ensure_initialized(self) -> None:
        if self._initialized is False:
            self.initialize()

    def _ensure_global_config_exists(self, quiet_init: bool = False) -> None:
        if self.global_config_path.exists() is True:
            return

        try:
            config_dir: Path = self.global_config_path.parent
            if config_dir.exists() is False:
                config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.global_config_path, "w", encoding="utf-8") as file_obj:
                json.dump(DEFAULT_CONFIG, file_obj, ensure_ascii=False, indent=2, sort_keys=True)
                file_obj.write("\n")
            if quiet_init is False:
                logger.warning(f"Seedling configuration initialized at: {self.global_config_path}")
        except OSError as err:
            raise ConfigurationWriteError(
                message=f"Failed to initialize Seedling configuration: {self.global_config_path}",
                context={"path": str(self.global_config_path)}
            ) from err

    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                loaded_config: Any = json.load(file_obj)
        except json.JSONDecodeError as err:
            raise ConfigurationCorruptionError(
                message=f"Malformed Seedling configuration: {file_path}",
                context={"path": str(file_path), "error": str(err)}
            ) from err
        except OSError as err:
            raise ConfigurationLoadError(
                message=f"Failed to read Seedling configuration: {file_path}",
                context={"path": str(file_path)}
            ) from err

        if isinstance(loaded_config, dict) is False:
            raise ConfigurationCorruptionError(
                message=f"Seedling configuration must be a JSON object: {file_path}",
                context={"path": str(file_path)}
            )

        self._validate_config_shape(loaded_config, file_path)
        return loaded_config

    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = copy.deepcopy(base)
        for key, value in override.items():
            if key in merged:
                if isinstance(merged[key], dict) is True:
                    if isinstance(value, dict) is True:
                        merged[key] = self._merge_config(merged[key], value)
                    else:
                        merged[key] = value
                else:
                    merged[key] = value
            else:
                merged[key] = value
        return merged

    def _resolve_config_path(self, raw_value: str) -> Path:
        candidate: Path = Path(raw_value).expanduser()
        if candidate.is_absolute() is True:
            return candidate.resolve(strict=False)
        return (self._cwd / candidate).resolve(strict=False)

    def _validate_config_shape(self, config: Dict[str, Any], file_path: Path) -> None:
        object_sections: Tuple[str, ...] = ("scan", "build", "clean", "preferences", "commands", "state")
        for section in object_sections:
            if section in config:
                if isinstance(config[section], dict) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section '{section}' must be an object: {file_path}",
                        context={"path": str(file_path), "section": section}
                    )

        if "scan" in config:
            scan_section: Dict[str, Any] = config["scan"]
            if "strip_comments" in scan_section:
                if isinstance(scan_section["strip_comments"], bool) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'scan.strip_comments' must be a boolean: {file_path}",
                        context={"path": str(file_path), "section": "scan.strip_comments"}
                    )

        if "preferences" in config:
            preferences_section: Dict[str, Any] = config["preferences"]
            if "output_format" in preferences_section:
                output_format = preferences_section["output_format"]
                if output_format is not None and isinstance(output_format, str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'preferences.output_format' must be a string or null: {file_path}",
                        context={"path": str(file_path), "section": "preferences.output_format"}
                    )
            if "default_scan_depth" in preferences_section:
                default_scan_depth = preferences_section["default_scan_depth"]
                if default_scan_depth is not None and isinstance(default_scan_depth, int) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'preferences.default_scan_depth' must be an integer or null: {file_path}",
                        context={"path": str(file_path), "section": "preferences.default_scan_depth"}
                    )
            if "show_hidden" in preferences_section:
                show_hidden = preferences_section["show_hidden"]
                if show_hidden is not None and isinstance(show_hidden, bool) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'preferences.show_hidden' must be a boolean or null: {file_path}",
                        context={"path": str(file_path), "section": "preferences.show_hidden"}
                    )
            if "build_output_dir" in preferences_section:
                build_output_dir = preferences_section["build_output_dir"]
                if build_output_dir is not None and isinstance(build_output_dir, str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'preferences.build_output_dir' must be a string or null: {file_path}",
                        context={"path": str(file_path), "section": "preferences.build_output_dir"}
                    )
            if "clean_strategy" in preferences_section:
                clean_strategy = preferences_section["clean_strategy"]
                if clean_strategy is not None and isinstance(clean_strategy, str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'preferences.clean_strategy' must be a string or null: {file_path}",
                        context={"path": str(file_path), "section": "preferences.clean_strategy"}
                    )
            if "common_excludes" in preferences_section:
                if isinstance(preferences_section["common_excludes"], list) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'preferences.common_excludes' must be a list: {file_path}",
                        context={"path": str(file_path), "section": "preferences.common_excludes"}
                    )

        if "commands" in config:
            commands_section: Dict[str, Any] = config["commands"]
            if "plugin_dirs" in commands_section:
                if isinstance(commands_section["plugin_dirs"], list) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'commands.plugin_dirs' must be a list: {file_path}",
                        context={"path": str(file_path), "section": "commands.plugin_dirs"}
                    )

        if "build" in config:
            build_section: Dict[str, Any] = config["build"]
            if "default_target" in build_section:
                default_target = build_section["default_target"]
                if default_target is not None and isinstance(default_target, str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'build.default_target' must be a string or null: {file_path}",
                        context={"path": str(file_path), "section": "build.default_target"}
                    )
            for field_name in ("force", "check", "direct", "allow_overwrite"):
                if field_name in build_section:
                    if isinstance(build_section[field_name], bool) is False:
                        raise ConfigurationCorruptionError(
                            message=f"Configuration section 'build.{field_name}' must be a boolean: {file_path}",
                            context={"path": str(file_path), "section": f"build.{field_name}"}
                        )

        if "clean" in config:
            clean_section: Dict[str, Any] = config["clean"]
            if "strategy" in clean_section:
                if isinstance(clean_section["strategy"], str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'clean.strategy' must be a string: {file_path}",
                        context={"path": str(file_path), "section": "clean.strategy"}
                    )
            if "dry_run_default" in clean_section:
                if isinstance(clean_section["dry_run_default"], bool) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'clean.dry_run_default' must be a boolean: {file_path}",
                        context={"path": str(file_path), "section": "clean.dry_run_default"}
                    )
            for field_name in ("recursive_dirs", "root_only_dirs", "extensions", "ignore_dirs", "custom_targets"):
                if field_name in clean_section:
                    if isinstance(clean_section[field_name], list) is False:
                        raise ConfigurationCorruptionError(
                            message=f"Configuration section 'clean.{field_name}' must be a list: {file_path}",
                            context={"path": str(file_path), "section": f"clean.{field_name}"}
                        )
            if "external_script" in clean_section:
                external_script = clean_section["external_script"]
                if external_script is not None and isinstance(external_script, str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'clean.external_script' must be a string or null: {file_path}",
                        context={"path": str(file_path), "section": "clean.external_script"}
                    )
            if "external_mode" in clean_section:
                if isinstance(clean_section["external_mode"], str) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'clean.external_mode' must be a string: {file_path}",
                        context={"path": str(file_path), "section": "clean.external_mode"}
                    )


config_manager: Final[AbstractConfigManager] = SeedlingConfigManager()
