# 🌲 Seedling (v2.3.1)

[![Seedling CI](https://img.shields.io/github/actions/workflow/status/bbpeaches/Seedling/ci.yml?branch=main&style=flat-square)](https://github.com/bbpeaches/Seedling/actions)
[![PyPI version](https://img.shields.io/pypi/v/seedling-tools.svg?style=flat-square&color=blue)](https://pypi.org/project/Seedling-tools/)
[![Python Versions](https://img.shields.io/pypi/pyversions/seedling-tools.svg?style=flat-square)](https://pypi.org/project/Seedling-tools/)
[![License](https://img.shields.io/github/license/bbpeaches/Seedling?style=flat-square)](https://github.com/bbpeaches/Seedling/blob/main/LICENSE)

**Seedling** 是一款专为开发者设计的高性能、三合一 CLI（命令行）工具箱，用于探索、搜索和重构目录结构。无论您是需要一张精美的项目架构图，想通过文本蓝图快速生成项目，还是需要为大语言模型（LLM）提取极度优化后的代码库骨架，Seedling 都能为您轻松搞定。

其他语言版本阅读: [🇬🇧 English](../README.md)

---

## 🛠️ 安装指南

Seedling 推荐通过 `pipx` 进行全局安装，以确保干净的隔离环境。
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

## 🐍 作为 Python 库使用

您现在可以通过 `ScanConfig` 引擎直接在 Python 代码中使用 Seedling 的核心功能：

```python
import seedling
from seedling.core.filesystem import ScanConfig

# 1. 初始化配置 (设置 quiet=True 以屏蔽 CLI 进度条输出)
config = ScanConfig(max_depth=2, quiet=True)

# 2. 生成目录树行
stats = {"dirs": 0, "files": 0}
lines = seedling.scan_dir_lines("./src", config, stats)
print("\n".join(lines))

# 3. 编程式搜索特定项目
exact, fuzzy = seedling.search_items(".", keyword="utils", config=config)

# 4. 从蓝图重建项目
seedling.build_structure_from_file("blueprint.md", "./new_project")
```

-----

## 📖 CLI 命令参考

Seedling 2.3.1 采用清晰、显式的参数系统。

### 1\. `scan` - 探索器

用于扫描目录、提取代码骨架或搜索项目。注意：`--full` 和 `--skeleton` 为互斥参数。

| 参数 | 描述 |
| --- | --- |
| `target` | 要扫描或搜索的目标目录 (默认为 `.`)。 |
| `--find`, `-f` | **搜索模式**。快速 CLI 搜索 (精确匹配 & 模糊匹配)。结合 `--full` 可导出代码报告。 |
| `--format`, `-F` | 输出格式：`md` (默认), `txt`, 或 `image`。 |
| `--name`, `-n` | 自定义输出文件名。 |
| `--outdir`, `-o` | 结果保存路径。 |
| `--showhidden` | 扫描时包含隐藏文件。 |
| `--depth`, `-d` | 最大递归深度。 |
| `--exclude`, `-e` | 排除项目列表。**智能解析：自动读取 `.gitignore` 文件或接受 Glob 模式**。 |
| `--full` | **强力模式 (Power Mode)**。附加所有扫描到的源文件的全文内容。 |
| `--skeleton` | **[实验性]** AST 代码骨架提取。剔除内部逻辑，保留签名。 |
| `--text` | **智能过滤**。仅扫描文本格式文件 (自动忽略二进制/多媒体文件)。 |
| `--delete` | **清理模式**。永久删除被 `--find` 匹配到的项目 (仅限交互式 TTY 终端可用)。 |
| `--verbose` / `-q`| 调试日志模式 (`-v`) 或静默模式 (`-q`)。 |

### 2\. `build` - 建造师

将基于文本的树状图蓝图转换为真实的文件系统，或从快照中恢复项目。

| 参数 | 描述 |
| --- | --- |
| `file` | 源树状图蓝图文件 (`.txt` 或 `.md`)。 |
| `target` | 构建结构的存放位置 (默认为当前目录)。 |
| `--direct`, `-d` | **直达模式**。跳过提示，立即创建指定路径。 |
| `--check` | **预检模式 (Dry-Run)**。模拟构建过程，报告缺失/已存在的项目。 |
| `--force` | **强制覆盖**。直接覆盖已存在的文件而不跳过。 |

-----

## 📂 项目结构 (v2.3.1)

```text
Seedling/
├── docs/                      # 文档与更新日志
│   ├── CHANGELOG.md           # 英文更新日志
│   ├── CHANGELOG_zh.md        # 中文更新日志
│   └── README_zh.md           # 中文说明文档
├── seedling/                  # 核心包 
│   ├── commands/              # CLI 命令路由
│   │   ├── build/             # 构建逻辑
│   │   └── scan/              # 扫描逻辑
│   ├── core/                  # 共享引擎
│   │   ├── filesystem.py      # 迭代 DFS，ScanConfig 与过滤机制
│   │   ├── io.py              # 文件读写，代码块边界碰撞与路径安全
│   │   ├── logger.py          # 集中式 CLI 格式化器
│   │   ├── sysinfo.py         # 硬件探针
│   │   └── ui.py              # 动画与 CI/CD 环境检查
│   ├── __init__.py            # 公开 API 与元数据
│   └── main.py                # CLI 入口路由
├── tests/                     # 单元测试 (核心、边缘场景与 IO)
├── install.bat                # Windows 一键安装脚本
├── install.sh                 # Linux/macOS 一键安装脚本
├── LICENSE                    # MIT 开源许可证
├── pyproject.toml             # 构建配置与包元数据
├── pytest.ini                 # Pytest 测试配置文件
├── README.md                  # 项目说明文档
└── test_suite.sh              # 自动化测试
```

-----

## 📜 变更日志

每一次发布的详细变更历史均记录于 [CHANGELOG.md](CHANGELOG.md) 文件中。
