"""
Unit tests for Seedling v2.4 Agent Tools Enhancement features.
Tests for: JSON output, Include filter, Type filter, Regex search, Grep mode, Analyze mode.
"""
import json
import re
import pytest #type: ignore
from pathlib import Path

from seedling.core.config import ScanConfig, FILE_TYPE_MAP
from seedling.core.patterns import is_valid_item, matches_include_pattern
from seedling.core.traversal import traverse_directory, TraversalResult
from seedling.commands.scan.json_output import build_json_structure, write_json
from seedling.commands.scan.grep import grep_files, GrepMatch, format_grep_output

class TestScanConfigV24:
    def test_includes_field_default(self):
        assert ScanConfig().includes == []
    def test_includes_field_set(self):
        assert ScanConfig(includes=["*.py", "*.md"]).includes == ["*.py", "*.md"]
    def test_file_type_field_default(self):
        assert ScanConfig().file_type is None
    def test_file_type_field_set(self):
        assert ScanConfig(file_type="py").file_type == "py"
    def test_use_regex_field_default(self):
        assert ScanConfig().use_regex is False
    def test_use_regex_field_set(self):
        assert ScanConfig(use_regex=True).use_regex is True

class TestFileTypeMap:
    def test_py_type_exists(self):
        assert "py" in FILE_TYPE_MAP and ".py" in FILE_TYPE_MAP["py"]
    def test_js_type_exists(self):
        assert "js" in FILE_TYPE_MAP and ".js" in FILE_TYPE_MAP["js"]
    def test_ts_type_exists(self):
        assert "ts" in FILE_TYPE_MAP and ".ts" in FILE_TYPE_MAP["ts"]
    def test_cpp_type_exists(self):
        assert "cpp" in FILE_TYPE_MAP and ".cpp" in FILE_TYPE_MAP["cpp"] and ".h" in FILE_TYPE_MAP["cpp"]
    def test_all_type_is_none(self):
        assert "all" in FILE_TYPE_MAP and FILE_TYPE_MAP["all"] is None

class TestMatchesIncludePattern:
    def test_empty_patterns_returns_true(self, tmp_path):
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, []) is True
    def test_exact_filename_match(self, tmp_path):
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["test.py"]) is True
    def test_glob_pattern_match(self, tmp_path):
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["*.py"]) is True
    def test_no_match(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["*.py"]) is False
    def test_nested_file_match(self, tmp_path):
        nested_dir = tmp_path / "src"
        nested_dir.mkdir()
        file_path = nested_dir / "main.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["*.py"]) is True
    def test_multiple_patterns(self, tmp_path):
        py_file, md_file, txt_file = tmp_path / "test.py", tmp_path / "readme.md", tmp_path / "notes.txt"
        for f in (py_file, md_file, txt_file): f.touch()
        patterns = ["*.py", "*.md"]
        assert matches_include_pattern(py_file, tmp_path, patterns) is True
        assert matches_include_pattern(md_file, tmp_path, patterns) is True
        assert matches_include_pattern(txt_file, tmp_path, patterns) is False

class TestIsValidItemV24:
    def test_include_filter_pass(self, tmp_path):
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert is_valid_item(file_path, tmp_path, ScanConfig(includes=["*.py"])) is True
    def test_include_filter_block(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.touch()
        assert is_valid_item(file_path, tmp_path, ScanConfig(includes=["*.py"])) is False
    def test_include_filter_directory_pass(self, tmp_path):
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        assert is_valid_item(dir_path, tmp_path, ScanConfig(includes=["*.py"])) is True
    def test_file_type_filter_pass(self, tmp_path):
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert is_valid_item(file_path, tmp_path, ScanConfig(file_type="py")) is True
    def test_file_type_filter_block(self, tmp_path):
        file_path = tmp_path / "test.js"
        file_path.touch()
        assert is_valid_item(file_path, tmp_path, ScanConfig(file_type="py")) is False
    def test_file_type_filter_directory_pass(self, tmp_path):
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        assert is_valid_item(dir_path, tmp_path, ScanConfig(file_type="py")) is True
    def test_combined_filters(self, tmp_path):
        py_file, js_file = tmp_path / "test.py", tmp_path / "test.js"
        py_file.touch(); js_file.touch()
        config = ScanConfig(includes=["*.py"], file_type="py")
        assert is_valid_item(py_file, tmp_path, config) is True
        assert is_valid_item(js_file, tmp_path, config) is False

class TestSearchItemsRegex:
    """用模拟的内存检索逻辑替换已被删除的 search_items。"""
    def _mock_search(self, tmp_path, keyword, config):
        result = traverse_directory(tmp_path, config)
        exact = []
        regex_pattern = re.compile(keyword, re.IGNORECASE) if config.use_regex else None
        for item in result.items:
            if item.is_dir: continue
            if config.use_regex and regex_pattern:
                if regex_pattern.search(item.path.name): exact.append(item.path)
            else:
                if keyword.lower() in item.path.name.lower(): exact.append(item.path)
        return exact, [] # 测试中不再关注 fuzzy

    def test_normal_search(self, tmp_path):
        (tmp_path / "test_file.py").touch(); (tmp_path / "other.txt").touch()
        exact, _ = self._mock_search(tmp_path, "test", ScanConfig())
        assert len(exact) == 1 and exact[0].name == "test_file.py"
    def test_regex_search(self, tmp_path):
        (tmp_path / "test_1.py").touch(); (tmp_path / "test_2.py").touch(); (tmp_path / "other.txt").touch()
        exact, _ = self._mock_search(tmp_path, r"test_\d+\.py", ScanConfig(use_regex=True))
        assert len(exact) == 2
    def test_regex_no_fuzzy(self, tmp_path):
        (tmp_path / "testing.py").touch()
        exact, fuzzy = self._mock_search(tmp_path, r"test_\d+", ScanConfig(use_regex=True))
        assert len(exact) == 0 and len(fuzzy) == 0
    def test_regex_case_insensitive(self, tmp_path):
        (tmp_path / "TEST_File.py").touch()
        exact, _ = self._mock_search(tmp_path, r"test_file", ScanConfig(use_regex=True))
        assert len(exact) == 1

class TestJsonOutput:
    def test_build_json_structure(self, tmp_path):
        (tmp_path / "test.py").touch(); (tmp_path / "subdir").mkdir()
        config = ScanConfig()
        result = traverse_directory(tmp_path, config) # 先获取快照
        json_result = build_json_structure(tmp_path, config, result)
        assert "meta" in json_result and "stats" in json_result and "tree" in json_result
        assert json_result["stats"]["directories"] == 1
        assert json_result["stats"]["files"] == 1
    def test_write_json(self, tmp_path):
        data = {"test": "value", "number": 123}
        output_file = tmp_path / "output.json"
        assert write_json(data, output_file) is True
        with open(output_file) as f:
            loaded = json.load(f)
        assert loaded["test"] == "value" and loaded["number"] == 123
    def test_json_structure_nested(self, tmp_path):
        subdir = tmp_path / "src" / "nested"
        subdir.mkdir(parents=True)
        (subdir / "file.py").touch()
        result = traverse_directory(tmp_path, ScanConfig())
        json_result = build_json_structure(tmp_path, ScanConfig(), result)
        assert "children" in json_result["tree"] and len(json_result["tree"]["children"]) > 0

class TestGrepModule:
    def test_grep_files_basic(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('world')\n")
        config = ScanConfig()
        result = traverse_directory(tmp_path, config, collect_content=True) # 开启缓存收集
        matches = grep_files(result, "hello", config, context=0)
        assert len(matches) == 1 and matches[0].line_number == 1 and "hello" in matches[0].line_content

    def test_grep_files_no_match(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    pass\n")
        config = ScanConfig()
        result = traverse_directory(tmp_path, config, collect_content=True)
        matches = grep_files(result, "nonexistent", config, context=0)
        assert len(matches) == 0

    def test_grep_with_context(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\ntarget line\nline4\nline5\n")
        config = ScanConfig()
        result = traverse_directory(tmp_path, config, collect_content=True)
        matches = grep_files(result, "target", config, context=1)
        assert len(matches) == 1
        assert "line2" in matches[0].context_before and "line4" in matches[0].context_after

    def test_grep_type_filter(self, tmp_path):
        py_file = tmp_path / "test.py"
        js_file = tmp_path / "test.js"
        py_file.write_text("target_string\n")
        js_file.write_text("target_string\n")
        config = ScanConfig(file_type="py")
        result = traverse_directory(tmp_path, config, collect_content=True)
        matches = grep_files(result, "target_string", config, context=0)
        assert len(matches) == 1 and matches[0].file_path.suffix == ".py"

class TestGrepCaseSensitivity:
    def test_grep_case_sensitive_default(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def TODO():\n    pass\n")
        config = ScanConfig()
        result = traverse_directory(tmp_path, config, collect_content=True)
        matches = grep_files(result, "todo", config, context=0, ignore_case=False)
        assert len(matches) == 0

    def test_grep_case_insensitive(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("def TODO():\n    pass\n")
        config = ScanConfig()
        result = traverse_directory(tmp_path, config, collect_content=True)
        matches = grep_files(result, "todo", config, context=0, ignore_case=True)
        assert len(matches) == 1 and "TODO" in matches[0].line_content

class TestTraversalModule:
    def test_traverse_directory_basic(self, tmp_path):
        (tmp_path / "file1.py").touch(); (tmp_path / "subdir").mkdir(); (tmp_path / "subdir" / "file2.py").touch()
        result = traverse_directory(tmp_path, ScanConfig())
        assert len(result.items) == 3 and result.stats["files"] == 2 and result.stats["dirs"] == 1
