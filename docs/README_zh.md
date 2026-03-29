# Seedling-tools

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling-tools** 是一款高性能的命令行工具包，专为代码库探索、智能分析以及大模型上下文聚合而设计。

核心功能：
1. **SCAN**：将目录树结构导出为 Markdown、TXT、JSON 或图片格式。
2. **FIND & GREP**：执行精确/模糊的文件名搜索，以及基于正则表达式的文件内容匹配。
3. **ANALYZE**：自动探测项目架构、核心依赖包及程序入口点。
4. **SKELETON**：基于 AST 提取 Python 代码结构，并自动剥离具体的实现逻辑。
5. **POWER MODE**：全量聚合整个代码仓库的源码，为 LLM 提示词投喂提供完整的上下文。
6. **BUILD**：根据纯文本蓝图逆向还原出真实的物理文件系统。

由统一单次遍历缓存引擎强力驱动。

其他语言版本阅读: [English](../README.md)

---

## 安装指南

Seedling-tools 推荐通过 `pipx` 进行全局安装，以确保干净的隔离环境。
```bash
pipx install Seedling-tools
```

### 一键安装脚本

* **Windows**: 运行 `./install.bat`
* **macOS / Linux**: 运行 `bash install.sh`

### 开发者 / 手动安装

如果您需要修改源代码，请使用**可编辑模式 (Editable Mode)**：

```bash
pipx install -e . --force
```

---

## 作为 Python 库使用

您现在可以通过直接在 Python 代码中使用 Seedling 的核心功能：

```python
import seedlingtools
from pathlib import Path
from seedlingtools.core import ScanConfig, DepthFirstTraverser, StandardTreeRenderer

# 初始化配置
config = ScanConfig(max_depth=2, quiet=True)

# 获取内存快照
traverser = DepthFirstTraverser()
result = traverser.traverse(Path("./src"), config)

# 渲染树状线条
renderer = StandardTreeRenderer()
lines = renderer.render(result, config)
print("\n".join(lines))
```

---

## CLI 命令参考

Seedling-tools 采用清晰、显式的参数系统。

### 1. `scan`

用于扫描目录、提取代码骨架或搜索项目。注意：`--full` 和 `--skeleton` 为互斥参数。

| 参数 | 描述 |
| --- | --- |
| `target` | 要扫描或搜索的目标目录 (默认为 `.`)。 |
| `--find`, `-f` | **搜索模式**。快速 CLI 搜索 (精确匹配 & 模糊匹配)。结合 `--full` 可导出代码报告。 |
| `--format`, `-F` | 输出格式：`md` (默认), `txt`, `json`, 或 `image`。 |
| `--name`, `-n` | 自定义输出文件名。 |
| `--outdir`, `-o` | 结果保存路径。 |
| `--showhidden` | 扫描时包含隐藏文件。 |
| `--depth`, `-d` | 最大递归深度。 |
| `--exclude`, `-e` | 排除项目列表。**智能解析：自动读取 `.gitignore` 文件或接受 Glob 模式**。 |
| `--include` | 仅包含匹配模式的文件/目录 (如 `--include "*.py"`)。 |
| `--type`, `-t` | 按文件类型过滤：`py`, `js`, `ts`, `cpp`, `go`, `java`, `rs`, `web`, `json`, `yaml`, `md`, `shell`, `all`。 |
| `--regex` | 将 `-f` 搜索模式视为正则表达式。 |
| `--grep`, `-g` | 在文件内容中搜索 (内容搜索模式)。 |
| `-C`, `--context` | 在 grep 匹配周围显示 N 行上下文。 |
| `--analyze` | 分析项目结构、类型、依赖和架构。 |
| `--full` | **强力模式 (Power Mode)**。附加所有扫描到的源文件的全文内容。 |
| `--skeleton` | **[实验性]** AST 代码骨架提取。剔除内部逻辑，保留签名。 |
| `--text` | **智能过滤**。仅扫描文本格式文件 (自动忽略二进制/多媒体文件)。 |
| `--delete` | **清理模式**。永久删除被 `--find` 匹配到的项目 (仅限交互式 TTY 终端可用)。 |
| `--dry-run` | 预览删除操作但不实际执行 (配合 `--delete` 使用)。 |
| `--verbose` / `-q`| 调试日志模式 (`-v`) 或静默模式 (`-q`)。 |

### 2. `build`

将基于文本的树状图蓝图转换为真实的文件系统，或从快照中恢复项目。

| 参数 | 描述 |
| --- | --- |
| `file` | 源树状图蓝图文件 (`.txt` 或 `.md`)。 |
| `target` | 构建结构的存放位置 (默认为当前目录)。 |
| `--direct`, `-d` | **直达模式**。跳过提示，立即创建指定路径。 |
| `--check` | **预检模式 (Dry-Run)**。模拟构建过程，报告缺失/已存在的项目。 |
| `--force` | **强制覆盖**。直接覆盖已存在的文件而不跳过。 |

---

## v2.5 新功能

### 模块化插件与编排系统
- **扫描管线 (Scan)**：高级扫描模式 (`--analyze`, `--grep`, `--skeleton`, `--find`) 现已通过 `ScanOrchestrator` 引擎实现插件化。
- **构建管线 (Build)**：逆向构建模式现已全面升级为 `BuildOrchestrator` 对称编排架构，彻底解耦了拓扑解析 (Parsers)、预检拦截 (Plugins, 如 `--check`) 与物理写入 (Executors)。

### 统一基础设施
- 将底层文件 I/O、安全越权校验与系统交互集中到健壮的全局单例实例中 (`logger`, `terminal`, `io_processor`, `image_renderer`)。
- 引入了统一的异常体系 (`SeedlingToolsError` 及其派生类)，提供更精确、包含调试上下文的领域级错误报告。

### 功能预留
- **接口预留**：架构层已提前挂载 **Token 统计属性**、**XML 结构化导出**以及**远程仓库克隆扫描**的逻辑钩子，为下个版本的 LLM 增强功能打好了地基。

---

## 项目结构 (v2.5)

```text
Seedling/
├── docs/                      # 文档与更新日志     
├── seedlingtools/             # 核心包
│   ├── commands/              # CLI 命令路由
│   │   ├── build/             # 逆向构建管线
│   │   └── scan/              # 扫描分析管线
│   ├── core/                  # 共享核心引擎     
│   ├── utils/                 # 全局基础设施   
│   ├── __init__.py            # API 与包元数据
│   └── main.py                # CLI 入口调度器
├── tests/                     # Unit Test            
├── install.bat                
├── install.sh                 
├── LICENSE                    
├── pyproject.toml             
├── pytest.ini                 
├── README.md                  
└── test_suite.sh              # E2E 自动化测试
```

---

## 变更日志

每一次发布的详细变更历史均记录于 [docs/CHANGELOG.md](https://github.com/bbpeaches/Seedling/blob/main/docs/CHANGELOG.md) 文件中。