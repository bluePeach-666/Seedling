import pytest #type: ignore
from pathlib import Path
from seedlingtools import ScanConfig
from seedlingtools.core import (
    detect_text_file, 
    probe_binary_signature,
    evaluate_exclusion_rules,
    validate_scan_target
)

def test_text_detection():
    assert detect_text_file(Path("main.py")) is True
    assert detect_text_file(Path("Dockerfile")) is True
    assert detect_text_file(Path("data.bin")) is False

def test_binary_probing(tmp_path):
    bin_file = tmp_path / "test.png"
    bin_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    assert probe_binary_signature(bin_file) is True
    
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Normal Text Content", encoding='utf-8')
    assert probe_binary_signature(txt_file) is False

def test_exclusion_logic(tmp_path):
    base = tmp_path
    (base / "build").mkdir()
    (base / "src/build").mkdir(parents=True)
    
    rules = ["/build/"]
    assert evaluate_exclusion_rules(base / "build", base, rules) is True
    assert evaluate_exclusion_rules(base / "src/build", base, rules) is False

def test_scan_target_validation(tmp_path):
    base = tmp_path
    config = ScanConfig(show_hidden=False, file_type="py")
    
    py_file = base / "main.py"
    py_file.touch()
    assert validate_scan_target(py_file, base, config) is True
    
    hidden_file = base / ".env"
    hidden_file.touch()
    assert validate_scan_target(hidden_file, base, config) is False
