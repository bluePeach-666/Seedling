from __future__ import annotations
import subprocess
import tempfile
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final

from .log_helper import logger
from .exceptions import SystemProbeError, FileSystemError
from .patterns import SingletonMeta

class AbstractGitHelper(ABC):
    @abstractmethod
    def clone_repository(self, url: str) -> Path:
        pass

    @abstractmethod
    def cleanup_repository(self, path: Path) -> None:
        pass

class SubprocessGitHelper(AbstractGitHelper, metaclass=SingletonMeta):
    def clone_repository(self, url: str) -> Path:
        try:
            temp_dir_path: str = tempfile.mkdtemp(prefix="seedling_repo_")
            target_path: Path = Path(temp_dir_path)
            logger.info(f"Cloning remote repository {url} to temporary directory...")
            
            process_result: subprocess.CompletedProcess[str] = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(target_path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if process_result.returncode != 0:
                raise SystemProbeError(
                    message=f"Git clone operation failed with exit code {process_result.returncode}",
                    hint="Check your network connection, repository URL, and Git credentials.",
                    context={"stderr": process_result.stderr}
                )
            
            return target_path
            
        except FileNotFoundError as err:
            raise SystemProbeError(
                message="Git executable not found in system PATH.",
                hint="Please install Git and ensure it is available in your environment variables."
            ) from err
        except OSError as err:
            raise FileSystemError(
                message="Failed to create temporary directory for repository cloning.",
                hint="Check system temporary directory permissions and available space."
            ) from err

    def cleanup_repository(self, path: Path) -> None:
        if path.exists() is True:
            if path.is_dir() is True:
                try:
                    shutil.rmtree(path)
                    logger.debug(f"Temporary repository cleaned up: {path}")
                except OSError as err:
                    logger.warning(f"Failed to clean up temporary directory {path}: {err}")

gitter: Final[AbstractGitHelper] = SubprocessGitHelper()