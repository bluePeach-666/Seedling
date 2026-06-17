# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
from pathlib import Path

from seedlingtools.core.comment_stripper import CommentStripper


def test_python_comment_stripping_preserves_strings_and_removes_comments(tmp_path: Path) -> None:
    source_file: Path = tmp_path / "example.py"
    source_file.write_text(
        "\"\"\"module doc\"\"\"\n"
        "value = '# not a comment'\n"
        "# remove me\n"
        "def demo():\n"
        "    \"\"\"function doc\"\"\"\n"
        "    return value  # trailing\n",
        encoding="utf-8"
    )

    stripper = CommentStripper()
    result = stripper.strip_file(source_file)

    assert "module doc" not in result.stripped_text
    assert "function doc" not in result.stripped_text
    assert "# remove me" not in result.stripped_text
    assert "trailing" not in result.stripped_text
    assert "'# not a comment'" in result.stripped_text


def test_inline_comment_stripping_preserves_strings(tmp_path: Path) -> None:
    source_file: Path = tmp_path / "example.ts"
    source_file.write_text(
        "const text = \"// not comment\";\n"
        "// remove line\n"
        "const next = 1; /* remove block */\n",
        encoding="utf-8"
    )

    stripper = CommentStripper()
    result = stripper.strip_file(source_file)

    assert "// remove line" not in result.stripped_text
    assert "remove block" not in result.stripped_text
    assert '"// not comment"' in result.stripped_text
    assert "const next = 1;" in result.stripped_text
