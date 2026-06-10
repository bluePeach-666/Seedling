from __future__ import annotations
import argparse
import copy
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Tuple

from .config import ScanConfig
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
        "template_path": None
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
    def initialize(self, cwd: Optional[Path] = None) -> None:
        pass

    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def build_scan_config(self, args: argparse.Namespace) -> ScanConfig:
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

    def initialize(self, cwd: Optional[Path] = None) -> None:
        self.global_config_path = Path.home() / ".seedling" / "config.json"
        self._ensure_global_config_exists()

        global_config: Dict[str, Any] = self._load_config_file(self.global_config_path)
        merged_config: Dict[str, Any] = self._merge_config(copy.deepcopy(DEFAULT_CONFIG), global_config)

        current_dir: Path = Path.cwd()
        if cwd is not None:
            current_dir = cwd

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
            template_path = Path(template_value).expanduser().resolve()
        if hasattr(args, "template") is True:
            if getattr(args, "template") is not None:
                template_path = Path(getattr(args, "template")).resolve()

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
            template_path=template_path
        )

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

    def _ensure_global_config_exists(self) -> None:
        if self.global_config_path.exists() is True:
            return

        try:
            config_dir: Path = self.global_config_path.parent
            if config_dir.exists() is False:
                config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.global_config_path, "w", encoding="utf-8") as file_obj:
                json.dump(DEFAULT_CONFIG, file_obj, ensure_ascii=False, indent=2, sort_keys=True)
                file_obj.write("\n")
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

    def _validate_config_shape(self, config: Dict[str, Any], file_path: Path) -> None:
        object_sections: Tuple[str, ...] = ("scan", "commands", "state")
        for section in object_sections:
            if section in config:
                if isinstance(config[section], dict) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section '{section}' must be an object: {file_path}",
                        context={"path": str(file_path), "section": section}
                    )

        if "commands" in config:
            commands_section: Dict[str, Any] = config["commands"]
            if "plugin_dirs" in commands_section:
                if isinstance(commands_section["plugin_dirs"], list) is False:
                    raise ConfigurationCorruptionError(
                        message=f"Configuration section 'commands.plugin_dirs' must be a list: {file_path}",
                        context={"path": str(file_path), "section": "commands.plugin_dirs"}
                    )


config_manager: Final[AbstractConfigManager] = SeedlingConfigManager()
