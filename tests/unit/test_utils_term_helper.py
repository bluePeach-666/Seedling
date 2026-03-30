# Unit tests for Seedling-tools v2.5.
# Copyright (c) 2026 Kaelen Chow. All rights reserved.

from __future__ import annotations
import pytest # type: ignore
from unittest.mock import patch

from seedlingtools.utils.term_helper import SeedlingTerminal

def test_prompt_confirmation_interactive_yes() -> None:
    term = SeedlingTerminal()
    with patch('sys.stdin.isatty', return_value=True), \
         patch('builtins.input', return_value='y'):
        result = term.prompt_confirmation("Proceed? [y/n]: ")
        assert result is True

def test_prompt_confirmation_interactive_no() -> None:
    term = SeedlingTerminal()
    with patch('sys.stdin.isatty', return_value=True), \
         patch('builtins.input', return_value='no'):
        result = term.prompt_confirmation("Proceed? [y/n]: ")
        assert result is False

def test_prompt_confirmation_non_interactive() -> None:
    term = SeedlingTerminal()
    
    with patch('sys.stdin.isatty', return_value=False):
        res_safe = term.prompt_confirmation("Delete everything?", default_no=True)
        assert res_safe is False
        res_force = term.prompt_confirmation("Auto-create folder?", default_no=False)
        assert res_force is True

def test_render_progress_quiet_mode(capsys: pytest.CaptureFixture[str]) -> None:
    term = SeedlingTerminal()
    term.render_progress(current=15, label="Scanning", quiet=True)

    captured = capsys.readouterr()
    assert captured.out == ""