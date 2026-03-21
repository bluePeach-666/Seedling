"""
Unit tests for Seedling v2.4 Agent Tools Enhancement features.
Tests for: JSON output, Include filter, Type filter, Regex search, Grep mode, Analyze mode.
"""
import json
import pytest
from pathlib import Path
from dataclasses import dataclass

from seedling.core.filesystem import (
    ScanConfig, is_valid_item, matches_include_pattern,
    search_items, FILE_TYPE_MAP
)
from seedling.commands.scan.json_output import build_json_structure, write_json
from seedling.commands.scan.grep import grep_files, GrepMatch, format_grep_output


class TestScanConfigV24:
    """Test new ScanConfig fields for v2.4."""

    def test_includes_field_default(self):
        """Test includes field defaults to empty list."""
        config = ScanConfig()
        assert config.includes == []

    def test_includes_field_set(self):
        """Test includes field can be set."""
        config = ScanConfig(includes=["*.py", "*.md"])
        assert config.includes == ["*.py", "*.md"]

    def test_file_type_field_default(self):
        """Test file_type field defaults to None."""
        config = ScanConfig()
        assert config.file_type is None

    def test_file_type_field_set(self):
        """Test file_type field can be set."""
        config = ScanConfig(file_type="py")
        assert config.file_type == "py"

    def test_use_regex_field_default(self):
        """Test use_regex field defaults to False."""
        config = ScanConfig()
        assert config.use_regex is False

    def test_use_regex_field_set(self):
        """Test use_regex field can be set."""
        config = ScanConfig(use_regex=True)
        assert config.use_regex is True


class TestFileTypeMap:
    """Test FILE_TYPE_MAP constant."""

    def test_py_type_exists(self):
        """Test Python file type mapping exists."""
        assert "py" in FILE_TYPE_MAP
        assert ".py" in FILE_TYPE_MAP["py"]

    def test_js_type_exists(self):
        """Test JavaScript file type mapping exists."""
        assert "js" in FILE_TYPE_MAP
        assert ".js" in FILE_TYPE_MAP["js"]

    def test_ts_type_exists(self):
        """Test TypeScript file type mapping exists."""
        assert "ts" in FILE_TYPE_MAP
        assert ".ts" in FILE_TYPE_MAP["ts"]

    def test_cpp_type_exists(self):
        """Test C++ file type mapping exists."""
        assert "cpp" in FILE_TYPE_MAP
        assert ".cpp" in FILE_TYPE_MAP["cpp"]
        assert ".h" in FILE_TYPE_MAP["cpp"]

    def test_all_type_is_none(self):
        """Test 'all' type mapping is None (matches everything)."""
        assert "all" in FILE_TYPE_MAP
        assert FILE_TYPE_MAP["all"] is None


class TestMatchesIncludePattern:
    """Test include pattern matching."""

    def test_empty_patterns_returns_true(self, tmp_path):
        """Empty patterns should always return True."""
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, []) is True

    def test_exact_filename_match(self, tmp_path):
        """Test matching exact filename."""
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["test.py"]) is True

    def test_glob_pattern_match(self, tmp_path):
        """Test matching glob pattern."""
        file_path = tmp_path / "test.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["*.py"]) is True

    def test_no_match(self, tmp_path):
        """Test non-matching pattern."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["*.py"]) is False

    def test_nested_file_match(self, tmp_path):
        """Test matching nested file."""
        nested_dir = tmp_path / "src"
        nested_dir.mkdir()
        file_path = nested_dir / "main.py"
        file_path.touch()
        assert matches_include_pattern(file_path, tmp_path, ["*.py"]) is True

    def test_multiple_patterns(self, tmp_path):
        """Test matching against multiple patterns."""
        py_file = tmp_path / "test.py"
        md_file = tmp_path / "readme.md"
        txt_file = tmp_path / "notes.txt"

        py_file.touch()
        md_file.touch()
        txt_file.touch()

        patterns = ["*.py", "*.md"]
        assert matches_include_pattern(py_file, tmp_path, patterns) is True
        assert matches_include_pattern(md_file, tmp_path, patterns) is True
        assert matches_include_pattern(txt_file, tmp_path, patterns) is False


class TestIsValidItemV24:
    """Test is_valid_item with new v2.4 filters."""

    def test_include_filter_pass(self, tmp_path):
        """Test include filter passes matching files."""
        file_path = tmp_path / "test.py"
        file_path.touch()
        config = ScanConfig(includes=["*.py"])
        assert is_valid_item(file_path, tmp_path, config) is True

    def test_include_filter_block(self, tmp_path):
        """Test include filter blocks non-matching files."""
        file_path = tmp_path / "test.txt"
        file_path.touch()
        config = ScanConfig(includes=["*.py"])
        assert is_valid_item(file_path, tmp_path, config) is False

    def test_include_filter_directory_pass(self, tmp_path):
        """Test include filter always passes directories (for traversal)."""
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        config = ScanConfig(includes=["*.py"])
        # Directories should pass through for traversal
        assert is_valid_item(dir_path, tmp_path, config) is True

    def test_file_type_filter_pass(self, tmp_path):
        """Test file type filter passes matching files."""
        file_path = tmp_path / "test.py"
        file_path.touch()
        config = ScanConfig(file_type="py")
        assert is_valid_item(file_path, tmp_path, config) is True

    def test_file_type_filter_block(self, tmp_path):
        """Test file type filter blocks non-matching files."""
        file_path = tmp_path / "test.js"
        file_path.touch()
        config = ScanConfig(file_type="py")
        assert is_valid_item(file_path, tmp_path, config) is False

    def test_file_type_filter_directory_pass(self, tmp_path):
        """Test file type filter doesn't affect directories."""
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        config = ScanConfig(file_type="py")
        assert is_valid_item(dir_path, tmp_path, config) is True

    def test_combined_filters(self, tmp_path):
        """Test combined include and type filters."""
        py_file = tmp_path / "test.py"
        js_file = tmp_path / "test.js"
        py_file.touch()
        js_file.touch()

        # Include *.py AND type=py should work
        config = ScanConfig(includes=["*.py"], file_type="py")
        assert is_valid_item(py_file, tmp_path, config) is True
        assert is_valid_item(js_file, tmp_path, config) is False


class TestSearchItemsRegex:
    """Test search_items with regex mode."""

    def test_normal_search(self, tmp_path):
        """Test normal substring search."""
        (tmp_path / "test_file.py").touch()
        (tmp_path / "other.txt").touch()
        config = ScanConfig()
        exact, fuzzy = search_items(tmp_path, "test", config)
        assert len(exact) == 1
        assert exact[0].name == "test_file.py"

    def test_regex_search(self, tmp_path):
        """Test regex pattern search."""
        (tmp_path / "test_1.py").touch()
        (tmp_path / "test_2.py").touch()
        (tmp_path / "other.txt").touch()
        config = ScanConfig(use_regex=True)
        exact, fuzzy = search_items(tmp_path, r"test_\d+\.py", config)
        assert len(exact) == 2

    def test_regex_no_fuzzy(self, tmp_path):
        """Test regex mode doesn't return fuzzy matches."""
        (tmp_path / "testing.py").touch()
        config = ScanConfig(use_regex=True)
        exact, fuzzy = search_items(tmp_path, r"test_\d+", config)
        # No exact matches, and no fuzzy matches in regex mode
        assert len(exact) == 0
        assert len(fuzzy) == 0

    def test_invalid_regex_returns_empty(self, tmp_path):
        """Test invalid regex pattern returns empty lists."""
        config = ScanConfig(use_regex=True)
        exact, fuzzy = search_items(tmp_path, "[invalid(", config)
        assert len(exact) == 0
        assert len(fuzzy) == 0

    def test_regex_case_insensitive(self, tmp_path):
        """Test regex search is case insensitive."""
        (tmp_path / "TEST_File.py").touch()
        config = ScanConfig(use_regex=True)
        exact, _ = search_items(tmp_path, r"test_file", config)
        assert len(exact) == 1


class TestJsonOutput:
    """Test JSON output module."""

    def test_build_json_structure(self, tmp_path):
        """Test building JSON structure."""
        (tmp_path / "test.py").touch()
        (tmp_path / "subdir").mkdir()

        config = ScanConfig()
        stats = {"dirs": 1, "files": 1}
        result = build_json_structure(tmp_path, config, stats)

        assert "meta" in result
        assert "stats" in result
        assert "tree" in result
        assert result["meta"]["root"] == tmp_path.name
        assert result["stats"]["directories"] == 1
        assert result["stats"]["files"] == 1

    def test_write_json(self, tmp_path):
        """Test writing JSON to file."""
        data = {"test": "value", "number": 123}
        output_file = tmp_path / "output.json"

        success = write_json(data, output_file)
        assert success is True
        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            loaded = json.load(f)
        assert loaded["test"] == "value"
        assert loaded["number"] == 123

    def test_json_structure_nested(self, tmp_path):
        """Test JSON structure with nested directories."""
        subdir = tmp_path / "src" / "nested"
        subdir.mkdir(parents=True)
        (subdir / "file.py").touch()

        config = ScanConfig()
        stats = {"dirs": 0, "files": 0}
        result = build_json_structure(tmp_path, config, stats)

        # Check tree has children
        tree = result["tree"]
        assert "children" in tree
        assert len(tree["children"]) > 0

    def test_json_file_extension(self, tmp_path):
        """Test JSON structure includes file extensions."""
        (tmp_path / "test.py").touch()
        (tmp_path / "readme.md").touch()

        config = ScanConfig()
        stats = {"dirs": 0, "files": 2}
        result = build_json_structure(tmp_path, config, stats)

        # Find files in tree
        def find_files(node):
            files = []
            if node["type"] == "file":
                files.append(node)
            if "children" in node:
                for child in node["children"]:
                    files.extend(find_files(child))
            return files

        files = find_files(result["tree"])
        extensions = {f.get("extension") for f in files}
        assert ".py" in extensions
        assert ".md" in extensions


class TestGrepModule:
    """Test grep (content search) module."""

    def test_grep_files_basic(self, tmp_path):
        """Test basic grep functionality."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    print('world')\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "hello", config, context=0)

        assert len(matches) == 1
        assert matches[0].line_number == 1
        assert "hello" in matches[0].line_content

    def test_grep_files_no_match(self, tmp_path):
        """Test grep with no matches."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "nonexistent", config, context=0)

        assert len(matches) == 0

    def test_grep_with_context(self, tmp_path):
        """Test grep with context lines."""
        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\ntarget line\nline4\nline5\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "target", config, context=1)

        assert len(matches) == 1
        assert len(matches[0].context_before) == 1
        assert len(matches[0].context_after) == 1
        assert "line2" in matches[0].context_before
        assert "line4" in matches[0].context_after

    def test_grep_with_regex(self, tmp_path):
        """Test grep with regex pattern."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def test_func():\ndef other():\n")

        config = ScanConfig(use_regex=True)
        matches = grep_files(tmp_path, r"def \w+\(\)", config, context=0)

        assert len(matches) == 2

    def test_grep_multiple_matches(self, tmp_path):
        """Test grep with multiple matches in same file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo():\ndef bar():\ndef baz():\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "def", config, context=0)

        assert len(matches) == 3

    def test_grep_type_filter(self, tmp_path):
        """Test grep respects file type filter."""
        py_file = tmp_path / "test.py"
        js_file = tmp_path / "test.js"
        py_file.write_text("target_string\n")
        js_file.write_text("target_string\n")

        config = ScanConfig(file_type="py")
        matches = grep_files(tmp_path, "target_string", config, context=0)

        assert len(matches) == 1
        assert matches[0].file_path.suffix == ".py"

    def test_format_grep_output(self, tmp_path):
        """Test formatting grep output."""
        matches = [
            GrepMatch(
                file_path=tmp_path / "test.py",
                relative_path=Path("test.py"),
                line_number=1,
                line_content="def hello():",
                context_before=["# comment"],
                context_after=["    pass"]
            )
        ]

        output = format_grep_output(matches, show_context=True)
        assert "test.py:1" in output
        assert "def hello():" in output

    def test_format_grep_output_no_context(self, tmp_path):
        """Test formatting grep output without context."""
        matches = [
            GrepMatch(
                file_path=tmp_path / "test.py",
                relative_path=Path("test.py"),
                line_number=1,
                line_content="def hello():",
                context_before=[],
                context_after=[]
            )
        ]

        output = format_grep_output(matches, show_context=False)
        assert "test.py:1" in output
        assert "def hello():" in output


class TestGrepMatch:
    """Test GrepMatch dataclass."""

    def test_grep_match_creation(self, tmp_path):
        """Test creating a GrepMatch instance."""
        match = GrepMatch(
            file_path=tmp_path / "test.py",
            relative_path=Path("test.py"),
            line_number=10,
            line_content="some code",
            context_before=["line 8", "line 9"],
            context_after=["line 11", "line 12"]
        )

        assert match.line_number == 10
        assert match.line_content == "some code"
        assert len(match.context_before) == 2
        assert len(match.context_after) == 2


class TestGrepCaseSensitivity:
    """Test grep case sensitivity control (v2.4.1)."""

    def test_grep_case_sensitive_default(self, tmp_path):
        """Test default grep is case-sensitive."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def TODO():\n    pass\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "todo", config, context=0, ignore_case=False)

        assert len(matches) == 0  # 'todo' should NOT match 'TODO'

    def test_grep_case_insensitive(self, tmp_path):
        """Test grep with ignore_case=True."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def TODO():\n    pass\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "todo", config, context=0, ignore_case=True)

        assert len(matches) == 1  # 'todo' should match 'TODO'
        assert "TODO" in matches[0].line_content

    def test_grep_case_sensitive_exact_match(self, tmp_path):
        """Test case-sensitive exact match."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def Todo():\ndef todo():\n")

        config = ScanConfig()
        matches = grep_files(tmp_path, "todo", config, context=0, ignore_case=False)

        # Should only match lowercase 'todo', not 'Todo'
        assert len(matches) == 1
        assert matches[0].line_content == "def todo():"

    def test_grep_regex_with_ignore_case(self, tmp_path):
        """Test regex mode respects ignore_case."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def TODO():\ndef todo():\n")

        config = ScanConfig(use_regex=True)
        # With case-sensitive, should only match lowercase 'todo'
        matches = grep_files(tmp_path, r"todo", config, context=0, ignore_case=False)
        assert len(matches) == 1
        assert "todo()" in matches[0].line_content

        # With case-insensitive, should match both
        matches = grep_files(tmp_path, r"todo", config, context=0, ignore_case=True)
        assert len(matches) == 2


class TestScanConfigIgnoreCase:
    """Test ScanConfig ignore_case field (v2.4.1)."""

    def test_ignore_case_field_default(self):
        """Test ignore_case field defaults to False."""
        config = ScanConfig()
        assert config.ignore_case is False

    def test_ignore_case_field_set(self):
        """Test ignore_case field can be set."""
        config = ScanConfig(ignore_case=True)
        assert config.ignore_case is True


class TestTraversalModule:
    """Test unified traversal module (v2.4.1)."""

    def test_traverse_directory_basic(self, tmp_path):
        """Test basic directory traversal."""
        from seedling.core.traversal import traverse_directory, TraversalItem

        (tmp_path / "file1.py").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.py").touch()

        config = ScanConfig()
        result = traverse_directory(tmp_path, config)

        assert len(result.items) == 3  # file1.py, subdir, file2.py
        assert result.stats["files"] == 2
        assert result.stats["dirs"] == 1

    def test_traversal_result_text_files(self, tmp_path):
        """Test TraversalResult.text_files list."""
        from seedling.core.traversal import traverse_directory

        (tmp_path / "code.py").touch()
        (tmp_path / "data.json").touch()
        (tmp_path / "image.png").touch()

        config = ScanConfig()
        result = traverse_directory(tmp_path, config)

        # Should only include text files
        text_names = {item.path.name for item in result.text_files}
        assert "code.py" in text_names
        assert "data.json" in text_names
        assert "image.png" not in text_names

    def test_traversal_content_cache(self, tmp_path):
        """Test content caching in traversal."""
        from seedling.core.traversal import traverse_directory

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        config = ScanConfig()
        result = traverse_directory(tmp_path, config, collect_content=True)

        # Find the item and check cached content
        for item in result.text_files:
            if item.path.name == "test.py":
                content = result.get_content(item, quiet=True)
                assert content == "print('hello')"
                break
        else:
            assert False, "test.py not found in text_files"

    def test_traversal_respects_depth_limit(self, tmp_path):
        """Test traversal respects max_depth."""
        from seedling.core.traversal import traverse_directory

        # Create nested structure
        (tmp_path / "l1").mkdir()
        (tmp_path / "l1" / "l2").mkdir()
        (tmp_path / "l1" / "l2" / "l3").mkdir()
        (tmp_path / "l1" / "l2" / "l3" / "deep.txt").touch()

        config = ScanConfig(max_depth=2)
        result = traverse_directory(tmp_path, config)

        # Should not include l3 or deep.txt
        all_paths = [item.path.name for item in result.items]
        assert "l3" not in all_paths
        assert "deep.txt" not in all_paths
