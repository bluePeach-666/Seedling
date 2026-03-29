from __future__ import annotations
import fnmatch
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set
from dataclasses import dataclass, field
from ..base import AbstractScanPlugin
from ..base import AbstractScanPlugin
from ....core import ScanConfig, TraversalResult
from ....utils import logger, FileSystemError, FileSettings, terminal

@dataclass
class ProjectAnalysis:
    """存储分析结果的数据容器"""
    project_type: str = "Unknown"                                    
    language: str = "Unknown"                                        
    entry_points: List[str] = field(default_factory=list)            
    config_files: List[str] = field(default_factory=list)            
    dependencies: Dict[str, List[str]] = field(default_factory=dict) 
    architecture: List[str] = field(default_factory=list)            
    file_stats: Dict[str, int] = field(default_factory=dict)         


class AnalyzerPlugin(AbstractScanPlugin):
    """项目特征分析插件"""
    
    def execute(self, target_path: Path, config: ScanConfig, result: TraversalResult, **kwargs: Any) -> None:
        out_file: Path = kwargs.get('out_file', Path.cwd() / f"{target_path.name}_analysis.md")
        
        if out_file.exists():
            if not terminal.prompt_confirmation(f"Target file {out_file.name} exists. Overwrite? [y/n]: "):
                logger.info("Analysis export aborted by user.")
                return

        analysis: ProjectAnalysis = self._analyze(result)

        logger.info("=" * 50)
        logger.info("Project Analysis Results")
        logger.info("=" * 50)
        logger.info(f"  Type: {analysis.project_type}")
        logger.info(f"  Language: {analysis.language}")
        logger.info(f"  Architecture: {', '.join(analysis.architecture) or 'Not detected'}")
        logger.info(f"  Entry Points: {len(analysis.entry_points)}")
        for ep in analysis.entry_points[:5]:
            logger.info(f"    - {ep}")
        logger.info(f"  Config Files: {', '.join(analysis.config_files[:5]) or 'None found'}")
        logger.info(f"  Dependencies: {len(analysis.dependencies.get('direct', []))} direct, {len(analysis.dependencies.get('dev', []))} dev")

        top_exts: List[Tuple[str, int]] = sorted(analysis.file_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_exts:
            logger.info(f"  Top Extensions: {', '.join(f'{ext}({cnt})' for ext, cnt in top_exts)}")

        try:
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(f"# Project Analysis: {target_path.name}\n\n")
                f.write(f"**Type**: {analysis.project_type}\n**Language**: {analysis.language}\n**Path**: `{target_path}`\n\n")
                
                f.write("## Architecture\n")
                for arch in analysis.architecture:
                    f.write(f"- {arch}\n")
                if not analysis.architecture:
                    f.write("No architectural patterns detected.\n")
                
                f.write("\n## Entry Points\n")
                for ep in analysis.entry_points:
                    f.write(f"- `{ep}`\n")
                
                f.write("\n## Configuration Files\n")
                for cf in analysis.config_files:
                    f.write(f"- `{cf}`\n")
                
                f.write("\n## Dependencies\n")
                f.write(f"### Direct ({len(analysis.dependencies.get('direct', []))})\n")
                for dep in analysis.dependencies.get('direct', []):
                    f.write(f"- {dep}\n")
                f.write(f"\n### Dev ({len(analysis.dependencies.get('dev', []))})\n")
                for dep in analysis.dependencies.get('dev', []):
                    f.write(f"- {dep}\n")
                
                f.write("\n## File Statistics\n")
                for ext, count in sorted(analysis.file_stats.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"| `{ext}` | {count} |\n")

            logger.info(f"Analysis saved to: {out_file}")
            
        except OSError as err:
            raise FileSystemError(
                message=f"Failed to save analysis report to {out_file.name}",
                context={"path": str(out_file)}
            ) from err

    def _analyze(self, result: TraversalResult) -> ProjectAnalysis:
        analysis = ProjectAnalysis()
        analysis.project_type, analysis.language = self._detect_type(result)
        analysis.config_files = self._find_configs(result, analysis.project_type)
        analysis.entry_points = self._find_entries(result, analysis.language)
        analysis.dependencies = self._extract_deps(result, analysis.project_type)
        analysis.architecture = self._detect_arch(result)
        analysis.file_stats = self._collect_stats(result)
        return analysis

    def _detect_type(self, result: TraversalResult) -> Tuple[str, str]:
        detected_types: List[Tuple[str, int]] = []
        for ptype, sig in FileSettings.PROJECT_SIGNATURES.items():
            score: int = 0
            for config_file in sig['files']:
                if any(item.path.name == config_file and item.depth == 1 for item in result.items):
                    score += 10
            if 'ext' in sig:
                for ext in sig['ext']:
                    count: int = sum(1 for item in result.items if not item.is_dir and item.path.suffix.lower() == ext)
                    score += min(count, 5)
            if score > 0:
                detected_types.append((ptype, score))
                
        if detected_types:
            detected_types.sort(key=lambda x: x[1], reverse=True)
            return detected_types[0][0], detected_types[0][0]
        return "generic", "unknown"

    def _find_configs(self, result: TraversalResult, ptype: str) -> List[str]:
        config_patterns: Dict[str, List[str]] = {
            'python': ['pyproject.toml', 'requirements*.txt', 'setup.py', 'setup.cfg', 'Pipfile'],
            'node': ['package.json', 'tsconfig.json', 'tsconfig.*.json', '.eslintrc*', '.prettierrc*'],
            'go': ['go.mod', 'go.sum'],
            'rust': ['Cargo.toml', 'Cargo.lock'],
            'java': ['pom.xml', 'build.gradle*', 'settings.gradle*'],
            'cpp': ['CMakeLists.txt', 'Makefile', '*.cmake']
        }
        found: List[str] = []
        for pattern in config_patterns.get(ptype, []):
            for item in result.items:
                if not item.is_dir and item.depth <= 2 and fnmatch.fnmatch(item.path.name, pattern):
                    found.append(item.path.name)
        return list(set(found))

    def _find_entries(self, result: TraversalResult, lang: str) -> List[str]:
        patterns: List[str] = FileSettings.ENTRY_PATTERNS.get(lang, [])
        if not patterns:
            return []
        entries: List[str] = []
        for item in result.text_files:
            if len(entries) >= 10:
                break
            content: str | None = result.get_content(item, quiet=True)
            if content:
                for p in patterns:
                    if re.search(p, content):
                        entries.append(str(item.relative_path))
                        break
        return entries

    def _extract_deps(self, result: TraversalResult, ptype: str) -> Dict[str, List[str]]:
        deps: Dict[str, List[str]] = {'direct': [], 'dev': []}
        for item in result.text_files:
            if item.depth > 2: 
                continue 
            
            if ptype == 'node' and item.path.name == 'package.json':
                content: str | None = result.get_content(item, quiet=True)
                if content:
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            deps['direct'] = list(data.get('dependencies', {}).keys())[:20]
                            deps['dev'] = list(data.get('devDependencies', {}).keys())[:10]
                    except json.JSONDecodeError:
                        pass
                    
            elif ptype == 'python' and item.path.name == 'requirements.txt':
                content = result.get_content(item, quiet=True)
                if content:
                    lines: List[str] = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#')]
                    deps['direct'] = [l.split('==')[0].split('>=')[0].split('[')[0] for l in lines[:20]]
                    
            elif ptype == 'rust' and item.path.name == 'Cargo.toml':
                content = result.get_content(item, quiet=True)
                if content:
                    in_deps: bool = False
                    for line in content.split('\n'):
                        stripped_line: str = line.strip()
                        if stripped_line == '[dependencies]':
                            in_deps = True
                            continue
                        if stripped_line.startswith('['):
                            in_deps = False
                        if in_deps and '=' in line and not stripped_line.startswith('#'):
                            dep_name: str = line.split('=')[0].strip()
                            if dep_name:
                                deps['direct'].append(dep_name)
        return deps

    def _detect_arch(self, result: TraversalResult) -> List[str]:
        dirs: Set[str] = {item.path.name.lower() for item in result.directories if item.depth == 1}
        hints: List[str] = []
        if {'controllers', 'models', 'views'} & dirs:
            hints.append('MVC')
        if {'services', 'repositories'} & dirs:
            hints.append('Layered')
        if {'domain', 'usecases', 'infrastructure'} & dirs:
            hints.append('Clean')
        if 'src' in dirs and ('tests' in dirs or 'test' in dirs):
            hints.append('SRC-TEST')
        if '.github' in dirs or any(item.path.name == '.gitlab-ci.yml' for item in result.items if item.depth==1):
            hints.append('CI/CD')
        if 'packages' in dirs or 'apps' in dirs:
            hints.append('Monorepo')
        return hints

    def _collect_stats(self, result: TraversalResult) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for item in result.items:
            if not item.is_dir:
                ext: str = item.path.suffix.lower() or '.no_ext'
                stats[ext] = stats.get(ext, 0) + 1
        return stats