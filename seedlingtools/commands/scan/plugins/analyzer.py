from __future__ import annotations
import fnmatch
import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set, Optional, Final
from dataclasses import dataclass, field

from ..base import AbstractScanPlugin
from ....core import ScanConfig, TraversalResult, StandardTreeRenderer
from ....utils import logger, FileSystemError, FileSettings, terminal, io_processor

@dataclass
class ProjectAnalysis:
    project_type: str = "Unknown"                                     
    language: str = "Unknown"                                        
    entry_points: List[str] = field(default_factory=list)            
    config_files: List[str] = field(default_factory=list)            
    dependencies: Dict[str, List[str]] = field(default_factory=dict) 
    architecture: List[str] = field(default_factory=list)            
    file_stats: Dict[str, int] = field(default_factory=dict)         


class AnalyzerPlugin(AbstractScanPlugin):
    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        out_file: Path
        if 'out_file' in kwargs:
            out_file = kwargs['out_file']
        else:
            out_file = Path.cwd() / f"{target_path.name}_analysis.md"
        
        if out_file.exists() is True:
            if terminal.prompt_confirmation(f"Target file {out_file.name} exists. Overwrite? [y/n]: ") is False:
                logger.info("Analysis export aborted by user.")
                sys.exit(0)

        analysis: ProjectAnalysis = self._analyze(target_path, result)

        logger.info("=" * 50)
        logger.info("Project Analysis Results")
        logger.info("=" * 50)
        logger.info(f"  Type: {analysis.project_type}")
        logger.info(f"  Language: {analysis.language}")
        
        arch_str: str = ""
        if len(analysis.architecture) > 0:
            arch_str = ", ".join(analysis.architecture)
        else:
            arch_str = "Not detected"
        logger.info(f"  Architecture: {arch_str}")
        
        logger.info(f"  Entry Points: {len(analysis.entry_points)}")
        for ep in analysis.entry_points[:5]:
            logger.info(f"    - {ep}")
            
        cfg_str: str = ""
        if len(analysis.config_files) > 0:
            cfg_str = ", ".join(analysis.config_files[:5])
        else:
            cfg_str = "None found"
        logger.info(f"  Config Files: {cfg_str}")
        
        direct_cnt: int = 0
        if 'direct' in analysis.dependencies:
            direct_cnt = len(analysis.dependencies['direct'])
            
        dev_cnt: int = 0
        if 'dev' in analysis.dependencies:
            dev_cnt = len(analysis.dependencies['dev'])
            
        logger.info(f"  Dependencies: {direct_cnt} direct, {dev_cnt} dev")

        def _sort_stats(x: Tuple[str, int]) -> int:
            return x[1]
            
        stats_items: List[Tuple[str, int]] = []
        for k, v in analysis.file_stats.items():
            stats_items.append((k, v))
            
        top_exts: List[Tuple[str, int]] = sorted(stats_items, key=_sort_stats, reverse=True)[:5]
        if len(top_exts) > 0:
            ext_strs: List[str] = []
            for ext, cnt in top_exts:
                ext_strs.append(f"{ext}({cnt})")
            logger.info(f"  Top Extensions: {', '.join(ext_strs)}")

        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(f"# Project Analysis: {target_path.name}\n\n")
                f.write(f"**Type**: {analysis.project_type}\n")
                f.write(f"**Language**: {analysis.language}\n")
                f.write(f"**Path**: `{target_path}`\n\n")
                
                f.write("## Architecture\n")
                if len(analysis.architecture) > 0:
                    for arch in analysis.architecture:
                        f.write(f"- {arch}\n")
                else:
                    f.write("No architectural patterns detected.\n")
                
                f.write("\n## Entry Points\n")
                for ep in analysis.entry_points:
                    f.write(f"- `{ep}`\n")
                
                f.write("\n## Configuration Files\n")
                for cf in analysis.config_files:
                    f.write(f"- `{cf}`\n")
                
                f.write("\n## Dependencies\n")
                f.write(f"### Direct ({direct_cnt})\n")
                if 'direct' in analysis.dependencies:
                    for dep in analysis.dependencies['direct']:
                        f.write(f"- {dep}\n")
                    
                f.write(f"\n### Dev ({dev_cnt})\n")
                if 'dev' in analysis.dependencies:
                    for dev_dep in analysis.dependencies['dev']:
                        f.write(f"- {dev_dep}\n")
                
                f.write("\n## File Statistics\n")
                sorted_all_stats: List[Tuple[str, int]] = sorted(stats_items, key=_sort_stats, reverse=True)
                for ext, count in sorted_all_stats:
                    f.write(f"| `{ext}` | {count} |\n")

            logger.info(f"Analysis metadata saved to: {out_file.name}")
            
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to save analysis report to {out_file.name}",
                context={"path": str(out_file)}
            ) from err

    def _analyze(self, target_path: Path, result: TraversalResult) -> ProjectAnalysis:
        analysis = ProjectAnalysis()
        
        detected_type: str
        detected_lang: str
        detected_type, detected_lang = self._detect_type(target_path, result)
        analysis.project_type = detected_type
        analysis.language = detected_lang
        
        analysis.config_files = self._find_configs(target_path, analysis.project_type)
        analysis.architecture = self._detect_arch(target_path)
        analysis.dependencies = self._extract_deps(target_path, analysis.project_type)
        analysis.entry_points = self._find_entries(target_path, result, analysis.language)
        analysis.file_stats = self._collect_stats(result)
        
        return analysis

    def _detect_type(self, target_path: Path, result: TraversalResult) -> Tuple[str, str]:
        detected_types: List[Tuple[str, int]] = []
        
        for ptype, sig in FileSettings.PROJECT_SIGNATURES.items():
            score: int = 0
            
            if 'files' in sig:
                for config_file in sig['files']:
                    test_path: Path = target_path / config_file
                    if test_path.is_file() is True:
                        score += 20
                    
            if 'ext' in sig:
                for ext in sig['ext']:
                    count: int = 0
                    for item in result.items:
                        if item.is_dir is False:
                            if item.path.suffix.lower() == ext:
                                count += 1
                                
                    if count < 10:
                        score += count
                    else:
                        score += 10
                        
            if score > 0:
                detected_types.append((ptype, score))
                
        def _sort_score(x: Tuple[str, int]) -> int:
            return x[1]
                
        if len(detected_types) > 0:
            detected_types.sort(key=_sort_score, reverse=True)
            return detected_types[0][0], detected_types[0][0]
            
        return "generic", "unknown"

    def _find_configs(self, target_path: Path, ptype: str) -> List[str]:
        config_patterns: Final[Dict[str, List[str]]] = {
            'python': ['pyproject.toml', 'requirements*.txt', 'setup.py', 'setup.cfg', 'Pipfile'],
            'node': ['package.json', 'tsconfig.json', 'tsconfig.*.json', '.eslintrc*', '.prettierrc*'],
            'go': ['go.mod', 'go.sum'],
            'rust': ['Cargo.toml', 'Cargo.lock'],
            'java': ['pom.xml', 'build.gradle*', 'settings.gradle*'],
            'cpp': ['CMakeLists.txt', 'Makefile', '*.cmake']
        }
        
        found: List[str] = []
        try:
            for item_path in target_path.iterdir():
                if item_path.is_file() is True:
                    fname: str = item_path.name
                    
                    if ptype in config_patterns:
                        patterns: List[str] = config_patterns[ptype]
                        for pattern in patterns:
                            if fnmatch.fnmatch(fname, pattern) is True:
                                found.append(fname)
        except OSError:
            pass
            
        unique_found: List[str] = []
        for f in found:
            if f not in unique_found:
                unique_found.append(f)
                
        return unique_found

    def _extract_deps(self, target_path: Path, ptype: str) -> Dict[str, List[str]]:
        deps: Dict[str, List[str]] = {'direct': [], 'dev': []}
        
        if ptype == 'python':
            toml_path: Path = target_path / 'pyproject.toml'
            req_path: Path = target_path / 'requirements.txt'
            
            if toml_path.is_file() is True:
                content: Optional[str] = io_processor.read_text_safely(toml_path, quiet=True)
                if content is not None:
                    dep_block_match: Optional[re.Match[str]] = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
                    if dep_block_match is not None:
                        dep_content: str = dep_block_match.group(1)
                        pkg_matches: List[str] = re.findall(r'[\"\']([a-zA-Z0-9_\-\.\>\<\=\!]+)[\"\']', dep_content)
                        for pkg in pkg_matches:
                            if pkg not in deps['direct']:
                                deps['direct'].append(pkg)
                    
                    dev_block_match: Optional[re.Match[str]] = re.search(r'\[project\.optional-dependencies\](.*?)(?:\n\[|$)', content, re.DOTALL)
                    if dev_block_match is not None:
                        dev_content: str = dev_block_match.group(1)
                        dev_pkg_matches: List[str] = re.findall(r'[\"\']([a-zA-Z0-9_\-\.\>\<\=\!]+)[\"\']', dev_content)
                        for dev_pkg in dev_pkg_matches:
                            if dev_pkg not in deps['dev']:
                                deps['dev'].append(dev_pkg)
                            
            elif req_path.is_file() is True:
                content_req: Optional[str] = io_processor.read_text_safely(req_path, quiet=True)
                if content_req is not None:
                    raw_req_lines: List[str] = content_req.split('\n')
                    for req_line in raw_req_lines:
                        clean_req_line: str = req_line.strip()
                        if len(clean_req_line) > 0:
                            if clean_req_line.startswith('#') is False:
                                parsed_pkg: str = clean_req_line.split('==')[0].split('>=')[0].split('[')[0]
                                if parsed_pkg not in deps['direct']:
                                    deps['direct'].append(parsed_pkg)
                                    if len(deps['direct']) >= 20:
                                        break
                                    
        elif ptype == 'node':
            pkg_path: Path = target_path / 'package.json'
            if pkg_path.is_file() is True:
                content_node: Optional[str] = io_processor.read_text_safely(pkg_path, quiet=True)
                if content_node is not None:
                    try:
                        data: Any = json.loads(content_node)
                        if type(data) is dict:
                            if 'dependencies' in data:
                                direct_dict: Any = data['dependencies']
                                if type(direct_dict) is dict:
                                    for key in direct_dict.keys():
                                        if key not in deps['direct']:
                                            deps['direct'].append(key)
                                            if len(deps['direct']) >= 20:
                                                break
                            
                            if 'devDependencies' in data:
                                dev_dict: Any = data['devDependencies']
                                if type(dev_dict) is dict:
                                    for dev_key in dev_dict.keys():
                                        if dev_key not in deps['dev']:
                                            deps['dev'].append(dev_key)
                                            if len(deps['dev']) >= 10:
                                                break
                    except json.JSONDecodeError:
                        pass
                        
        return deps

    def _detect_arch(self, target_path: Path) -> List[str]:
        hints: List[str] = []
        try:
            dirs: List[str] = []
            for d in target_path.iterdir():
                if d.is_dir() is True:
                    if d.name.startswith('.') is False:
                        if d.name.lower() not in dirs:
                            dirs.append(d.name.lower())
                        
            if 'controllers' in dirs:
                if 'models' in dirs:
                    if 'views' in dirs:
                        hints.append('MVC')
                        
            if 'services' in dirs:
                if 'repositories' in dirs:
                    hints.append('Layered')
                    
            if 'domain' in dirs:
                if 'usecases' in dirs:
                    if 'infrastructure' in dirs:
                        hints.append('Clean')
                
            if 'src' in dirs:
                if 'tests' in dirs or 'test' in dirs:
                    hints.append('SRC-TEST (Standard App)')
            else:
                if 'tests' in dirs or 'test' in dirs:
                    non_pkg_dirs: Final[List[str]] = ['tests', 'test', 'docs', 'build', 'dist', 'scripts', 'venv', 'env']
                    has_pkg_dir: bool = False
                    for d in dirs:
                        if d not in non_pkg_dirs:
                            has_pkg_dir = True
                            break
                            
                    if has_pkg_dir is True:
                        hints.append('PKG-TEST (Standard Package)')
                        
            git_ci_file: Path = target_path / '.gitlab-ci.yml'
            if '.github' in dirs or git_ci_file.is_file() is True:
                hints.append('CI/CD Pipeline')
                
            if 'packages' in dirs or 'apps' in dirs:
                hints.append('Monorepo')
                
        except OSError:
            pass
            
        return hints

    def _find_entries(self, target_path: Path, result: TraversalResult, lang: str) -> List[str]:
        entries: List[str] = []
        
        if lang == 'python':
            toml_path: Path = target_path / 'pyproject.toml'
            if toml_path.is_file() is True:
                content: Optional[str] = io_processor.read_text_safely(toml_path, quiet=True)
                if content is not None:
                    scripts_block: Optional[re.Match[str]] = re.search(r'\[project\.scripts\](.*?)(?:\n\[|$)', content, re.DOTALL)
                    if scripts_block is not None:
                        script_lines: List[str] = scripts_block.group(1).split('\n')
                        for line in script_lines:
                            clean_line: str = line.strip()
                            if len(clean_line) > 0:
                                if clean_line.startswith('#') is False:
                                    match: Optional[re.Match[str]] = re.match(r'([a-zA-Z0-9_\-]+)\s*=\s*[\"\'](.+)[\"\']', clean_line)
                                    if match is not None:
                                        cmd_name: str = match.group(1)
                                        target: str = match.group(2)
                                        entries.append(f"CLI: {cmd_name} -> {target}")
        
        if len(entries) == 0:
            patterns: List[str] = []
            if lang in FileSettings.ENTRY_PATTERNS:
                patterns = FileSettings.ENTRY_PATTERNS[lang]
                
            if len(patterns) > 0:
                for item in result.text_files:
                    if len(entries) >= 10:
                        break
                        
                    content_file: Optional[str] = result.get_content(item, quiet=True)
                    if content_file is not None:
                        for p in patterns:
                            if re.search(p, content_file) is not None:
                                entries.append(str(item.relative_path))
                                break
                                
        return entries

    def _collect_stats(self, result: TraversalResult) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for item in result.items:
            if item.is_dir is False:
                ext: str = ""
                if len(item.path.suffix) > 0:
                    ext = item.path.suffix.lower()
                else:
                    ext = '.no_ext'
                    
                if ext in stats:
                    stats[ext] += 1
                else:
                    stats[ext] = 1
        return stats


class ContextInjectorPlugin(AbstractScanPlugin):
    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        out_file: Path
        if 'out_file' in kwargs:
            out_file = kwargs['out_file']
        else:
            out_file = Path.cwd() / f"{target_path.name}_analysis.md"
        
        try:
            with open(out_file, 'a', encoding='utf-8') as f:
                f.write("\n## Directory Tree\n")
                f.write("```text\n")
                
                tree_renderer: StandardTreeRenderer = StandardTreeRenderer()
                tree_lines: List[str] = tree_renderer.render(result, config, root_path=target_path)
                
                f.write(f"{target_path.name}/\n")
                if len(tree_lines) > 0:
                    for line in tree_lines:
                        f.write(line + "\n")
                f.write("```\n")

                is_full: bool = False
                if 'is_full' in kwargs:
                    if kwargs['is_full'] is True:
                        is_full = True
                        
                if is_full is True:
                    f.write("\n\n" + "="*60 + "\n")
                    f.write("FULL PROJECT CONTENT\n")
                    f.write("="*60 + "\n\n")
                    
                    for item in result.text_files:
                        content: Optional[str] = result.get_content(item, quiet=config.quiet)
                        if content is not None:
                            fence: str = io_processor.calculate_markdown_fence(content)
                            lang: str = ""
                            if len(item.path.suffix) > 0:
                                lang = item.path.suffix.lstrip('.')
                                
                            f.write(f"### FILE: {item.relative_path}\n")
                            f.write(f"{fence}{lang}\n")
                            f.write(f"{content}\n")
                            f.write(f"{fence}\n\n")

            logger.info("Context injection complete. Directory tree and source code appended.")
            
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to append context to {out_file.name}",
                context={"path": str(out_file)}
            ) from err