from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

from ....core import CommentStripper, ScanConfig, TraversalResult
from ....utils import FileSystemError, io_processor, logger, terminal
from ..base import AbstractScanPlugin


class StripCommentsPlugin(AbstractScanPlugin):
    def __init__(self, in_place: bool = False) -> None:
        self.in_place = in_place
        self._stripper = CommentStripper()

    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        out_file: Path
        if "out_file" in kwargs:
            out_file = kwargs["out_file"]
        else:
            out_file = Path.cwd() / f"{target_path.name}_stripped.md"

        strip_mapping = self._build_stripped_mapping(result, config)
        if len(strip_mapping) == 0:
            logger.info("No text files were available for comment stripping.")
            return

        if self.in_place is True:
            self._write_in_place(strip_mapping)
            logger.info(f"Comment stripping complete for {len(strip_mapping)} files.")
            return

        self._write_report(target_path, config, result, strip_mapping, out_file)
        logger.info(f"Comment stripping report saved to: {out_file}")

    def _build_stripped_mapping(self, result: TraversalResult, config: ScanConfig) -> Dict[str, str]:
        text_mapping: Dict[str, str] = {}
        for item in result.text_files:
            content = result.get_content(item, quiet=config.quiet)
            if content is None:
                continue
            text_mapping[str(item.relative_path)] = content
        return self._stripper.strip_mapping(text_mapping)

    def _write_in_place(self, stripped_mapping: Dict[str, str]) -> None:
        for rel_path, content in stripped_mapping.items():
            file_path = Path(rel_path)
            io_processor.write_text_safely(file_path, content)

    def _write_report(
        self,
        target_path: Path,
        config: ScanConfig,
        result: TraversalResult,
        stripped_mapping: Dict[str, str],
        out_file: Path,
    ) -> None:
        try:
            lines = [
                f"# Comment Stripping Report: `{target_path}`",
                "",
                f"**Files processed**: {len(stripped_mapping)}",
                "",
                "## Stripped Files",
            ]
            for item in result.text_files:
                rel_path = str(item.relative_path)
                if rel_path not in stripped_mapping:
                    continue
                stripped_content = stripped_mapping[rel_path]
                fence = io_processor.calculate_markdown_fence(stripped_content)
                lines.append(f"### FILE: {rel_path}")
                lines.append(f"{fence}text")
                lines.append(stripped_content.rstrip("\n"))
                lines.append(fence)
                lines.append("")

            final_text = "\n".join(lines).rstrip() + "\n"
            if out_file.exists() is True:
                if terminal.prompt_confirmation(f"Target file '{out_file.name}' already exists. Overwrite? [y/n]: ") is False:
                    logger.info("Strip comments report aborted by user.")
                    return
            with open(out_file, "w", encoding="utf-8") as file_obj:
                file_obj.write(final_text)
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to write stripped report to {out_file.name}",
                context={"path": str(out_file)}
            ) from err


__all__ = [
    "StripCommentsPlugin"
]
