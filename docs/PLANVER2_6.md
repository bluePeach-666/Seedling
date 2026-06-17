# Seedling-tools v2.6.0 后续任务重规划

更新时间：2026-06-17
目标版本：`2.6.0`

## 0. 版本目标与发布边界

本轮后续规划统一归入 `v2.6.0`。当前工作树已经具备 `clean`、配置基座、动态命令总线、Build glyph bug 修复等基础能力，因此 `2.6.0` 的定位不只是小修补，而是从“脚本型 CLI”升级为“可配置、可扩展、可服务大模型 agent 的工具平台”。

### v2.6.0 必须完成的核心主题

- 可配置：`scan/build/clean` 都能读取全局与本地配置。
- 可扩展：通过 `seedling` 根命令和插件/规格化工具配置扩展命令。
- 可安全删除：`clean` 支持策略，但必须有危险删除检测。
- 可压缩上下文：统计、注释剥离、skill 输出都服务于减少 LLM token。
- 可验证：新增功能都必须有 unit + e2e，危险路径必须有负向测试。

### 版本号修改要求

所有 v2.6.0 功能完成后，最终发布前需要统一修改：

- `pyproject.toml`
  - `version = "2.6.0"`
- README 中的版本描述、功能列表、命令示例。
- 如后续新增 `CHANGELOG.md`，需要添加 `v2.6.0` 变更摘要。
- 测试报告、文档标题统一使用 `Seedling-tools v2.6.0`。
- github 管线更新
---

## 1. 当前已完成基线

以下能力已经在当前工作树中完成，并作为后续任务的基础：

- 原生 `clean` 命令：入口为 `clean`，支持安全缓存清理和 `--dry-run`。
- Build tree glyph Bug 修复：`│`、`├`、`└` 等视觉连接符噪声不会再被误建成文件或目录，同时保留合法 glyph 文件名。
- Config 基座：支持 `~/.seedling/config.json` 全局配置、项目 `.seedling.json` 本地覆盖、配置损坏错误、状态持久化。
- Dynamic Command Bus：新增 `seedling` 根命令、内置 `scan/build/clean` 适配、外部命令插件加载、strict/non-strict 插件错误处理。
- 测试基线：unit + e2e 已覆盖上述能力，full suite 通过。

这些能力是 v2.6.0 的地基，后续不应该推倒重写，而应该在现有接口上扩展。

### 1.1 已完成的 v2.6.0 增量

- Phase 1：`build/clean` 配置化，`clean` 策略系统，风险检测与 `CleanRiskError` 已完成。
- Phase 2：`preferences` 配置层与 `seedling config show/set/unset/reset` 已完成。
- Phase 3：`.seedling/commands.json` 规格化工具、`seedling tools list/add/remove/validate/export` 与 generated tool 注册已完成。
- Phase 4：`seedling strip-comments` 与 `scan --strip-comments` 已完成，当前实现以 Python + 保守 inline comment 规则为主。
- 验证：上述增量已有 common 环境 `pytest` 与 e2e 覆盖通过。

### 1.2 仍未完成的部分

- Phase 5：代码统计模块（`seedling stats`、`scan --stats`）尚未开始。
- Phase 6：异常体系补全仅完成了 `CleanRiskError`，其余异常与统一错误格式仍未完成。
- Phase 7：Agent Skill 与 token 节省评估尚未开始。
- Phase 8：Build Oracle 高频生成式测试尚未开始。
- 配置策略补充任务：默认不生成项目根 `.seedling.json`；仅当全局配置显式启用“生成项目根本地配置”时才生成该文件。
- Release polish：README / CHANGELOG / CI / 最终发布文案尚未统一收尾。

---

## 2. 我的优化思考

### 2.1 不要把所有功能一次性塞进一个大重构

当前路线里有很多强相关能力：配置、插件、工具生成、clean 策略、stats、strip-comments、skill、Build Oracle。它们容易互相牵连。我的建议是保持“垂直切片”推进：每一轮做一个可以独立使用、独立测试、独立回滚的能力。

推荐切片方式：

1. 先把 `clean/build` 配置化和删除安全边界做牢。
2. 再做 `.seedling` 规格化工具，因为它依赖 command bus。
3. 再做 stats / strip-comments，因为它们是 agent skill 的底层材料。
4. 最后做 agent skill 和 token 对比，因为它依赖前面的上下文压缩能力。

### 2.2 `clean` 的策略系统必须安全优先，而不是灵活优先

`clean` 是会删除文件的命令。配置化后，风险会比固定白名单更高。因此优化重点不是“允许用户配置任何删除规则”，而是“允许用户配置，但每条删除规则都经过风险评估”。

必须避免：

- 配置里写了 `/`、`~`、`..`、仓库外路径。
- 通配符误删源码。
- 把 `src/`、`seedlingtools/` 这类源码目录当缓存删掉。
- 外部脚本绕过 Seedling 的安全检查。

建议把 `clean` 拆成三层：

- Strategy：决定候选删除目标。
- RiskGuard：评估候选目标是否危险。
- Executor：执行 dry-run 或真实删除。

### 2.3 插件系统和规格化工具系统要分层

当前已经有动态命令插件，这是 Python 代码级扩展。后续 `.seedling/commands.json` 是配置级扩展。两者不应该混在一起。

建议分层：

- Python Plugin：适合高级用户，能写完整 Python 类。
- Generated Tool：适合普通用户，通过 JSON/YAML 规格声明 shell/API 工具。
- Agent Temporary Tool：适合大模型临时补工具，默认只读、可过期、可删除。

这样可以避免所有工具都变成高权限 Python 插件。

### 2.4 统计与注释剥离应服务于 token 节省指标

代码统计和注释剥离不是孤立功能。它们应该成为后续 agent skill 的度量基础。

建议每个上下文压缩能力都输出：

- 原始 token 估算。
- 压缩后 token 估算。
- 节省 token 数。
- 节省百分比。
- 是否保留足够语义。

这样 README 里可以展示真实效果，而不是只说“减少 token”。

### 2.5 Build Oracle 不宜默认跑大规模 fuzz

高频生成式测试很重要，但不能拖慢每次 CI。建议分层：

- 默认 CI：小规模 deterministic fuzz，例如 32 到 64 轮。
- nightly / 手动：1000+ 轮。
- 失败必输出 seed。

这样能兼顾回归安全和 CI 速度。

---

## 3. Phase 1：Clean Strategy + build/clean 配置化

目标：让 `build` 和 `clean` 都能读取 `~/.seedling/config.json` 与项目 `.seedling.json`，同时让 `clean` 从固定白名单升级为可配置策略系统。

这是下一轮最推荐优先实现的任务。

### 当前状态

- 已完成。
- 现状包括：`build` 支持配置驱动的默认 target / check / overwrite；`clean` 支持 `python-standard` / `node-modules` / `aggressive` 策略、风险拦截、`candidates-only` 外部脚本模式。
- 已有相关 unit + e2e 覆盖通过。

### 3.1 build 配置

建议新增配置段：

```json
{
  "build": {
    "default_target": null,
    "force": false,
    "check": false,
    "direct": false,
    "allow_overwrite": false
  }
}
```

执行优先级：

- CLI 显式参数 > 本地 `.seedling.json` > 全局 `~/.seedling/config.json` > 内置默认值。

安全要求：

- `force`、overwrite 类行为不能被静默扩大风险。
- 若配置启用危险行为，首次执行应给出高可见警告。
- CI/headless 场景不能触发交互确认。

### 3.2 clean 配置

建议新增配置段：

```json
{
  "clean": {
    "strategy": "python-standard",
    "dry_run_default": false,
    "recursive_dirs": ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"],
    "root_only_dirs": ["build", "dist"],
    "extensions": [".pyc", ".pyo", ".pyd"],
    "ignore_dirs": [".git", ".venv", "venv", "env", ".env", "node_modules"],
    "custom_targets": [],
    "external_script": null
  }
}
```

### 3.3 预设 clean 策略

至少支持：

- `PythonStandard`
  - 删除 Python 缓存、pytest/mypy/ruff 缓存、根目录 build/dist、egg-info。
- `NodeModules`
  - 只在明确配置时处理 Node 相关缓存，不默认删除 `node_modules`。
- `Aggressive`
  - 删除更多构建缓存，但必须强制 dry-run 预检，真实删除前输出高风险提示。

### 3.4 外部 clean 脚本覆盖

支持外部脚本，但必须受控：

- 配置项：`clean.external_script`。
- 脚本只能接收上下文参数，例如 target、dry-run、strategy。
- 脚本输出候选删除列表，Seedling 仍然要经过 RiskGuard 检查。
- 不允许外部脚本直接绕过 Seedling 删除执行器。

推荐模式：

```json
{
  "clean": {
    "external_script": "scripts/custom_clean.py",
    "external_mode": "candidates-only"
  }
}
```

`candidates-only` 表示外部脚本只负责发现目标，最终删除仍由 Seedling 执行。

### 3.5 删除危险检测 RiskGuard

clean 必须增加删除风险评分器：

- 阻止删除根目录、HOME、仓库外路径、系统目录。
- 阻止通配规则展开到过多非缓存文件。
- 阻止删除源码目录，例如 `src/`、`seedlingtools/`、`tests/`。
- 区分浅层删除和递归删除。
- 对 `custom_targets` 做严格白名单和 dry-run 预检。
- 对 symlink 做明确策略：默认不跟随 symlink。

### 3.6 测试

- 单元测试：build/clean config merge、CLI 覆盖配置。
- 单元测试：`PythonStandard`、`NodeModules`、`Aggressive` 策略候选目标。
- 单元测试：RiskGuard 阻止 HOME、根目录、仓库外路径、源码目录。
- 单元测试：外部 clean 脚本只能返回 candidates，不能直接删除。
- E2E：配置 clean 策略后执行 `clean --dry-run` 和真实 clean。
- E2E：危险配置必须失败且不删除文件。

### 当前状态

- 已完成，以上测试项已落地。

---

## 4. Phase 2：记忆力与用户偏好系统

目标：让 Seedling 能记住用户偏好，并通过配置层稳定复用。

### 功能范围

- 在 `~/.seedling/config.json` 中扩展 `preferences`：
  - 上次使用的输出格式。
  - 常用排除规则。
  - 默认扫描深度。
  - 默认是否显示隐藏文件。
  - 常用 build 输出目录。
  - 常用 clean 策略。
- 保留 `state` 用于内部状态，不与用户偏好混用。
- 增加 CLI 子命令：
  - `seedling config show`
  - `seedling config set <key> <value>`
  - `seedling config unset <key>`
  - `seedling config reset`

### 优化建议

偏好记忆不要默认记录所有行为，而是只记录低风险偏好。比如输出格式可以记，删除目标不能记。这样能避免“工具越来越自动，但用户不知道它记住了什么”。

### 测试

- 单元测试：偏好读写、覆盖、删除、重置。
- E2E：`seedling config set` 后执行 `scan`，确认默认行为变化。
- 配置损坏时仍走 `ConfigurationCorruptionError`。

### 当前状态

- 已完成。
- `preferences` 已接入全局配置，并提供 `seedling config show/set/unset/reset`。

---

## 5. Phase 3：`.seedling` 规格化命令工具配置

目标：允许用户按固定格式声明新命令，Seedling 自动生成命令行工具，或接入 API，同时支持删除这些工具。

### 配置位置

建议使用项目级目录：

```text
.seedling/
  commands.json
  tools/
```

或继续支持项目根 `.seedling.json` 中的 `commands.generated` 段。

### 补充约束（项目根配置文件生成策略）

- 默认不自动生成项目根 `.seedling.json`。
- 只有当全局配置中显式开启“生成项目根本地配置文件”选项时，才允许创建该文件。
- 未开启该全局选项时，项目根保持无 `.seedling.json` 也应视为正常状态。

### 规格化命令格式

建议格式：

```json
{
  "commands": [
    {
      "name": "custom-audit",
      "description": "Run a project-specific audit",
      "type": "shell",
      "command": "python scripts/audit.py {target}",
      "args": [
        {"name": "target", "required": true},
        {"name": "label", "flag": "--label", "default": "local"}
      ]
    },
    {
      "name": "api-summary",
      "description": "Call an internal API and summarize output",
      "type": "api",
      "method": "POST",
      "url": "https://example.internal/summary",
      "headers_env": ["API_TOKEN"],
      "body_template": {"target": "{target}"}
    }
  ]
}
```

### 命令管理能力

新增命令建议：

- `seedling tools list`
- `seedling tools add <spec-file>`
- `seedling tools remove <name>`
- `seedling tools validate`
- `seedling tools export`

### 当前状态

- 已完成。
- 已支持 `.seedling/commands.json` 规格化工具，以及 `seedling tools list/add/remove/validate/export`。

### 安全要求

- shell 类型命令默认禁止危险字符拼接。
- API 类型命令禁止把 token 明文写入配置，只允许从环境变量读取。
- 删除工具只删除 Seedling 管理的工具配置，不删除用户脚本本体，除非明确确认。
- 工具名称不能覆盖内置 `scan/build/clean/config`。

### 测试

- 单元测试：schema 校验、命令生成、参数渲染、危险 shell 拦截。
- E2E：从 spec 添加工具、执行工具、删除工具、确认 help 消失。

### 当前状态

- 已完成第一版。
- shell spec 的危险 token 已拦截；API spec 的 header secret 只允许从环境变量读取。
- 仍待补充：项目根 `.seedling.json` 的“默认不生成，需全局开关显式启用后才生成”策略。

---

## 6. Phase 4：删除指定文件注释

目标：新增对指定文件的注释剥离能力，用于生成更干净的上下文或直接清理文件副本。

### 建议命令

```bash
seedling strip-comments path/to/file.py --out stripped.py
seedling strip-comments path/to/file.py --in-place
seedling scan . --full --strip-comments
```

### Python 处理策略

- 使用 `ast` 处理 docstring。
- 使用 `tokenize` 移除 `#` 注释，避免误伤字符串中的 `#`。
- 保留语义有效代码。
- 默认输出到新文件或报告，不默认原地覆盖。

### 其他语言处理策略

- 先支持保守规则：`//`、`/* */`。
- 必须避免误伤字符串字面量。
- 对难以安全解析的语言，默认只在报告模式中剥离，不做原地写入。

### 安全要求

- `--in-place` 必须要求明确参数，不作为默认行为。
- 支持 `--dry-run` 或 `--check` 查看会发生什么。
- 原地修改前建议自动备份或只允许 git clean 状态下执行。

### 测试

- Python docstring、行尾注释、字符串中 `#`。
- JS/TS/C 风格注释与字符串碰撞。
- E2E：剥离指定文件并确认原文件未被默认修改。

### 当前状态

- 已完成第一版。
- 当前已支持：`seedling strip-comments path --check/--out/--in-place`，以及 `scan --strip-comments`。
- Python 采用 `ast + tokenize`，其他语言先采用保守的 inline comment 规则。

---

## 7. Phase 5：代码统计模块

目标：统计代码总行数、空白行数、非空白代码行数，并接入 scan 报告。

### 统计字段

```json
{
  "statistics": {
    "total_lines": 1200,
    "blank_lines": 180,
    "non_blank_lines": 1020,
    "files_counted": 42
  }
}
```

### 命令形态

```bash
seedling stats .
scan . --stats
scan . --full --stats
```

### 统计规则

- 只统计文本文件。
- 复用现有 binary detection。
- 支持 include/exclude/file type 过滤。
- 可按文件类型分组。

### 优化建议

统计模块应该被设计成可复用服务，而不是只服务一个 CLI。后续 agent skill 的 token 对比也需要统计结果，所以建议将统计核心放在 core 层或独立 service 层。

### 测试

- 单元测试：普通行、空行、纯空格行。
- 单元测试：二进制跳过。
- E2E：Markdown / JSON 报告包含统计 metadata。

---

## 8. Phase 6：异常体系补全

目标：把 config/plugin 之外的 parser/build 错误也纳入统一异常体系。

### 新增异常建议

- `ParseArtifactError`
  - 用于 build tree glyph、蓝图解析、伪结构污染等问题。
- `BuildPlanError`
  - 用于解析成功但构建计划不合法。
- `CleanRiskError`
  - 用于 clean 删除风险检测失败。
- `ToolSpecError`
  - 用于 `.seedling/commands.json` 工具规格错误。
- `SkillExecutionError`
  - 用于 agent skill 执行失败。

### 优化建议

异常不只是分类，还应该有统一格式：

- message：用户能读懂的问题。
- hint：下一步怎么修。
- context：机器可读上下文，例如 path、command、config key。
- exit_code：保持 CLI 行为稳定。

### 测试

- 单元测试：所有新异常继承自 `SeedlingToolsError`。
- 单元测试：错误字符串包含 class name 和 hint。
- E2E：典型错误场景返回稳定 exit code。

---

## 9. Phase 7：Agent Skill 与 token 节省评估

目标：让大模型 agent 可以调用 Seedling skill，减少上下文 token，并量化节省效果；当缺少工具时，agent 可以用 Seedling 的工具生成能力补一个临时工具。

### Skill 方向

建议新增 `seedling skill` 子系统：

- `seedling skill list`
- `seedling skill run <skill-name>`
- `seedling skill measure <skill-name>`
- `seedling skill scaffold <name>`

### 减少 token 的 skill 示例

- `summarize-tree`：只输出结构摘要。
- `extract-interfaces`：只提取函数/class/API 签名。
- `changed-context`：只输出 git diff 相关上下文。
- `stats-summary`：输出代码统计，不输出源码。
- `grep-context`：只输出命中附近上下文。

### token 对比要求

每个 skill 需要输出：

```json
{
  "baseline_tokens": 50000,
  "skill_tokens": 8500,
  "saved_tokens": 41500,
  "saved_percent": 83.0
}
```

基线可以是：

- `scan --full` 的估算 token。
- skill 输出的估算 token。
- 使用现有 `TraversalResult.estimated_tokens` 或新增统一 token estimator。

### Agent 自动补工具能力

当 agent 缺少工具时，可以：

1. 生成 `.seedling/commands.json` 工具规格。
2. 运行 `seedling tools validate`。
3. 临时注册该工具。
4. 执行后输出结果。
5. 可选择 `seedling tools remove <name>` 清理。

### 安全要求

- agent 自动生成工具默认只允许读操作。
- 写文件、删除文件、API 调用、shell 执行必须进入严格安全检查。
- 自动工具必须有过期机制或临时标记。

### 测试

- 单元测试：token 估算和节省百分比。
- E2E：运行一个 skill 并输出节省报告。
- E2E：生成临时工具、执行、删除。

---

## 10. Phase 8：Build Oracle 高频生成式测试

目标：把现有 targeted regression 升级为可复现的高频生成式 Oracle 测试。

### 组件

- `VirtualNode` / `VirtualDirectory` / `VirtualFile` dataclass。
- 随机拓扑生成器。
- 噪声注入器。
- 蓝图序列化器。
- 物理文件系统 Oracle。
- seed 记录与复现。

### 约束

- 默认 CI 只跑小规模 deterministic fuzz。
- 大规模 1000+ iteration 放到 nightly 或手动命令。
- 每次失败必须输出 random seed。
- 每轮使用隔离临时目录。

### 优化建议

不要直接上 10000 次 CI。先做一个可复现、可读、失败输出足够好的小型 Oracle。只有当小型 Oracle 稳定后，再加高频模式。

---

## 11. 推荐执行顺序

1. `Clean Strategy + build/clean 配置化`
2. `记忆力/偏好命令增强`
3. `.seedling` 规格化工具配置与工具增删`
4. `删除指定文件注释`
5. `代码统计模块`
6. `异常体系补全`
7. `Agent skill + token 节省评估`
8. `Build Oracle 高频生成式测试`

理由：

- Clean/build 配置化直接复用刚完成的 config 基座。
- 偏好系统让后续工具行为有稳定记忆入口。
- 工具配置直接复用 command bus。
- 注释剥离和统计能为 agent skill 提供底层能力。
- 异常体系补全应在 agent skill 和 Oracle 大规模测试前完成，方便错误归因。
- Agent skill 最依赖前面所有基础设施。

---

## 12. 最终 README 修改说明

v2.6.0 全部功能完成后，README 需要统一更新，不能只补几个命令示例。

### README 必改内容

1. 标题或版本描述
   - 标注 `Seedling-tools v2.6.0`。
   - 描述从 “CLI toolkit” 升级为 “configurable and extensible CLI platform”。

2. Quick Start
   - 保留旧入口：
     - `scan`
     - `build`
     - `clean`
   - 新增根入口：
     - `seedling scan`
     - `seedling build`
     - `seedling clean`
     - `seedling --help`

3. Configuration
   - 解释 `~/.seedling/config.json`。
   - 解释项目 `.seedling.json`。
   - 说明优先级：CLI > local > global > defaults。
   - 给出 `scan/build/clean/commands/preferences` 示例。

4. Clean Strategy
   - 说明 `PythonStandard`、`NodeModules`、`Aggressive`。
   - 说明危险删除检测。
   - 说明 `--dry-run` 是检查删除结果的推荐方式。

5. Dynamic Commands
   - 说明 Python 插件命令。
   - 说明 `.seedling/commands.json` 规格化工具。
   - 说明 API 工具不保存明文 token。
   - 说明如何删除工具。

6. Strip Comments
   - 说明 `seedling strip-comments`。
   - 说明默认不原地覆盖。
   - 说明 Python 与其他语言支持边界。

7. Statistics
   - 说明 `seedling stats` 和 `scan --stats`。
   - 展示 total / blank / non_blank / files_counted 输出。

8. Agent Skills
   - 说明 skill 列表、运行、token 对比。
   - 展示 token 节省报告。
   - 说明 agent 临时工具的安全边界。

9. Testing
   - 更新测试说明：unit + e2e + deterministic fuzz。
   - 加入 Build Oracle 小规模与大规模模式说明。

10. Migration Notes
   - 告诉老用户：`scan/build/clean` 仍可用。
   - 新用户推荐使用 `seedling <command>`。
   - 配置文件自动初始化，不需要手写。

### README 不建议写的内容

- 不要把所有内部架构细节塞进 README。
- 不要把危险 clean 示例放在最前面。
- 不要鼓励用户把 token、密钥、绝对危险路径写进配置。
- 大规模 fuzz 和 agent 自动写工具应放在高级用法区域。

---

## 13. 下一步建议

下一轮优先做：`代码统计模块`。

理由：

- Phase 1–4 已经把配置、工具扩展、注释剥离铺好。
- `stats` 是后续 token 节省度量和 agent skill 的直接底层能力。
- 相比 skill / Oracle，它依赖更少，适合继续保持垂直切片推进。
