# Seedling-tools

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling-tools** 是一款高性能的命令行工具包，专为代码库探索、智能分析以及大模型上下文聚合而设计。

核心功能：
1. **SCAN**：将目录树结构序列化导出为 Markdown、TXT、JSON、XML 或高清图片格式。
2. **FIND & GREP**：执行精确或模糊的文件名搜索，以及基于正则表达式的跨文件全文内容匹配。
3. **ANALYZE**：自动探测项目架构模式、核心依赖包矩阵以及程序的命令入口点。
4. **SKELETON**：基于 AST 提取 Python 代码骨架，自动剥离底层实现逻辑，仅保留类与函数的顶层签名。
5. **POWER MODE**：全量聚合目标代码仓库的源码，内置 Token 消耗估算，为大模型提供极致纯净的上下文。
6. **TEMPLATE**：提示词模板，通过 `{{SEEDLING_CONTEXT}}` 占位符实现自动化上下文组装与 LLM 审查指令注入。
7. **REMOTE**：支持远程 Git URL，在独立沙箱中即时完成代码库的克隆、解析与安全销毁。
8. **BUILD**：解析纯文本拓扑蓝图，进行无冲突预检，并逆向还原构建出真实的物理文件系统。

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

-----

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

-----

## 命令行使用
Seedling-tools 的核心优势在于它能够干净、高效地将复杂的代码库聚合为可被 LLM 直接消化的结构化文本。

### 场景一：向 LLM 提供整个后端的上下文
如果你是一个 Python 开发者，需要让大模型帮你审查或重构后端的业务逻辑，你可以使用组合指令精确抓取所有的 Python 文件，排除掉不需要的缓存和测试文件：
```bash
scan . -t py -e .gitignore --full
```
这会生成一个带有目录树和全量源码的 Markdown 文件，同时自动过滤掉多媒体文件和非 Python 代码，节省宝贵的 Token。

### 场景二：基于提示词模板进行自动化审查
您可以预先编写好一个提示词文件。在模板中预留 `{{SEEDLING_CONTEXT}}` 占位符，Seedling 会在扫描结束后自动将生成的上下文注入该位置。例如，使用本项目中提供的官方示例模板 [docs/prompt\_example.md](https://github.com/bbpeaches/Seedling/blob/main/docs/prompt_example.md)：
```bash
scan . --full --template docs/prompt_example.md -o ./reports -n output_report.md -e ".gitignore"
```

### 场景三：即时扫描开源项目
无需手动 Clone 整个仓库，直接将远程 Git URL 传递给 Seedling，它将在临时目录完成克隆、分析与上下文聚合，并在结束后自动销毁清理：
```bash
scan [https://github.com/bbpeaches/Seedling.git](https://github.com/bbpeaches/Seedling.git) -t py --analyze --full
```

-----

## CLI 命令参考
Seedling-tools 采用清晰、显式的参数系统。

### 1. `scan`
用于扫描目录、提取代码骨架或搜索项目。注意：`--full` 和 `--skeleton` 为互斥参数。

| 参数 | 描述 |
| --- | --- |
| `target` | 要扫描或搜索的目标目录，**或远程 Git 仓库 URL**。 |
| `--find`, `-f` | **搜索模式**。快速 CLI 搜索。 |
| `--format`, `-F` | 输出格式：`md` (默认), `txt`, `json`, `xml` 或 `image`。 |
| `--name`, `-n` | 自定义输出的具体文件名。 |
| `--outdir`, `-o` | 结果保存的目标目录路径。 |
| `--nohidden` | 排除隐藏文件（v2.5.1+ 默认扫描隐藏文件，需显式声明此参数以执行屏蔽）。 |
| `--depth`, `-d` | 最大递归深度。 |
| `--exclude`, `-e` | 排除项目列表。**智能解析：自动读取 `.gitignore` 文件或接受 Glob 模式**。 |
| `--include` | 仅包含匹配模式的文件/目录 (如 `--include "*.py"`)。 |
| `--type`, `-t` | 按文件类型过滤：`py`, `js`, `ts`, `cpp`, `go`, `java`, `rs`, `web`, `json`, `yaml`, `md`, `shell`, `all`。 |
| `--regex` | 将 `-f` 或 `-g` 搜索模式视为正则表达式。 |
| `--grep`, `-g` | 在文件内容中进行匹配搜索。 |
| `-C`, `--context` | 在 grep 匹配结果周围显示 N 行上下文。 |
| `--analyze` | 分析项目宏观结构、类型、依赖和架构。 |
| `--template` | **提示词模板引擎**。传入包含 `{{SEEDLING_CONTEXT}}` 占位符的文件路径，自动进行上下文注入组合。 |
| `--full` | **Power Mode**。附加所有被扫描到的源文件的全文内容，并自动估算总 Token 消耗。 |
| `--skeleton` | **[实验性]** AST 代码骨架提取。自动剔除内部实现逻辑，仅保留类与函数的签名。 |
| `--text` | **智能过滤**。强制仅扫描文本格式文件。 |
| `--delete` | **清理模式**。永久删除被 `--find` 匹配到的项目。 |
| `--dry-run` | 预览删除操作但不实际执行物理删除，可配合 `--delete` 使用。 |
| `--verbose` / `-q`| 开启调试日志模式 (`-v`) 或静默模式 (`-q`)。 |

### 2. `build`
将基于文本的树状图蓝图转换为真实的文件系统，或从快照中恢复项目。

| 参数 | 描述 |
| --- | --- |
| `file` | 源树状图蓝图文件 (`.txt` 或 `.md`)。 |
| `target` | 构建结构的存放位置，默认为当前执行目录。 |
| `--direct`, `-d` | **直达模式**。跳过交互式提示，立即在磁盘创建指定的单个文件或文件夹路径。 |
| `--check` | **预检模式**。进行无冲突模拟构建，并报告缺失、已存在或内容不匹配的项目。 |
| `--force` | **强制覆盖**。直接覆盖物理磁盘上已存在且内容冲突的文件而不进行二次确认跳过。 |

-----

## v2.5 核心特性

### 智能交互与过滤
  - **文件拦截**：引入探测逻辑，自动识别并拦截 `node_modules`、`.DS_Store`、`__pycache__` 等项目杂讯。
  - **交互降级**：系统在单一搜索模式或非交互式环境下，自动降级为静默警告，不阻断核心工作流。

### 模块化插件与对称编排系统
  - **扫描管线 (Scan)**：高级扫描模式已通过 `ScanOrchestrator` 架构实现全插件化。
  - **构建管线 (Build)**：逆向构建模式升级为 `BuildOrchestrator` 对称编排架构，解耦了拓扑解析、预检拦截与物理写入。

### 大模型 (LLM) 增强上下文引擎
  - **结构化 XML 导出**：新增 `-F xml` 格式支持。
  - **Token 估算**：在每次完整扫描与聚合后，自动在终端和输出报告的头部追加基于启发式算法的 Token 消耗估算值。
  - **提示词模板**：新增 `--template` 参数。允许开发者传入自定义的审查提示词文件，Seedling 会在扫描结束后自动将全量代码上下文精准注入至 `{{SEEDLING_CONTEXT}}` 占位符中，生成可直接投喂的 Prompt。
  - **远程仓库扫描**：CLI 支持直接传入 Git HTTPS/SSH 链接。

### 统一基础设施
  - 将底层文件 I/O、安全越权校验、Git 生命周期调度与系统交互集中到健壮的全局单例实例中。
  - 引入了统一的异常体系，提供更精确、包含调试上下文的错误报告拦截。

-----

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
├── tests/                     # Unit Test 与 E2E 自动化测试 
├── install.bat                
├── install.sh                 
├── LICENSE                    
├── pyproject.toml             
├── pytest.ini                 
├── README.md         
└── test.sh      
```

-----

## 变更日志

每一次发布的详细变更历史均记录于 [docs/CHANGELOG.md](https://www.google.com/search?q=./CHANGELOG.md) 文件中。