import pytest #type: ignore
from pathlib import Path
from seedlingtools import io_processor, terminal

def test_markdown_fence_calculation():
    assert io_processor.calculate_markdown_fence("simple code") == "```"
    assert io_processor.calculate_markdown_fence("```\nnested\n```") == "````"

def test_path_security_boundary(tmp_path):
    safe_dir = tmp_path / "safe"
    safe_dir.mkdir()
    
    assert io_processor.validate_path_security(safe_dir / "file.txt", safe_dir) is True
    assert io_processor.validate_path_security(tmp_path / "outside.txt", safe_dir) is False

def test_blueprint_deserialization(tmp_path):
    blueprint = tmp_path / "bp.md"
    blueprint.write_text("""
### FILE: src/main.py
```python
print('hello')
```
""", encoding='utf-8')

    contents = io_processor.deserialize_fenced_blocks(blueprint)
    
    assert "src/main.py" in contents
    assert "print('hello')" in contents["src/main.py"]
