# 快捷键 DSL / 领域模型 / Karabiner 编译设计

目标：支持两类触发方式，并生成 Karabiner-Elements 的复杂规则 JSON。

- **Chord（同时按下多个键）**：例如 `d+f`、`right_command+h`
- **Sequence（按键序列）**：例如 `f18>w>v`

整体架构分为 **编译前端** 与 **编译后端**：

- **前端（DSL → 规则 IR）**：把字符串 DSL 解析成平台无关的快捷键规则（IR / AST）
- **后端（规则 IR → Karabiner JSON）**：把 IR lowering（落到具体实现）为 Karabiner manipulators/rules JSON

> 约束：`set_variable` 属于 Karabiner 的内部实现细节，不出现在前端 `Action` 中；后端可自由使用它完成 sequence 的状态管理。

---

## 术语：Lowering 是什么

Lowering 是编译器领域常见术语：把一个 **更抽象、更接近意图** 的表示（高层 IR）转换成一个 **更具体、更贴近目标平台** 的表示（低层 IR / 目标格式）。

在本项目中：

- 高层 IR：表达“触发器是 `f18>w>v`，动作是发出 `command+shift+option+1`”
- 低层表示：Karabiner 的 manipulators，包含 `variable_if` 条件、`set_variable` 状态机、reset 等细节

---

## 编译前端（DSL → 领域模型 IR）

### DSL 语法

分隔符：

- `>`：sequence 的 step 分隔
- `+`：chord 内组合（modifier 或 key）

示例：

- `f18>w>v`：三步 sequence
- `right_command+h`：带左右区分 modifier 的单步 chord
- `d+f`：同时按下两个普通键（simultaneous keys）

动作 DSL（只描述“发出一个 key chord”）：

- `command+shift+option+1`
- `left_command+left_control+l`

别名（alias，可选）：

- **modifier alias**（便于书写）：`cmd` → `command`，`ctrl` → `control`，`opt/alt` → `option`
- **key alias**（便于语义化命名）：例如 `leader_key` → `f18`

> alias 的来源来自配置文件（TOML 的 `[alias.*]`）；DSL 解析前先做 token 级别替换，再进入语法解析与 IR 构建。

### 配置格式（TOML）

> 配置文件只表达“用户可见意图”，不包含 Karabiner 的内部实现策略（例如 sequence 的状态机变量、reset 细节等）。

顶层：

- `version`: 配置版本（整数）
- `description`: 规则描述（字符串）

全局条件（对所有规则生效）：

```toml
[when]
applications = [
  "^com\\.jetbrains\\.",
  "^com\\.google\\.android\\.studio$",
]
```

alias（可选）：

```toml
[alias.key]
leader_key = "f18"

[alias.mod]
cmd  = "command"
ctrl = "control"
opt  = "option"
alt  = "option"
```

规则列表（核心）：

```toml
[[rule]]
trigger = "leader_key>w>v"
emit    = "cmd+shift+opt+1"
```

规则级条件（可选）：

```toml
[[rule]]
trigger = "leader_key>w>v"
emit    = "cmd+shift+opt+1"

  [rule.when]
  applications = ["^com\\.jetbrains\\."]
```

条件合并语义（建议）：

- 若存在 `rule.when.applications`：覆盖全局 `[when].applications`
- 若不存在：继承全局 `[when].applications`

字段命名说明：

- TOML 中使用 `trigger = "..."` 表达“这条规则的触发器”
- 领域模型中对应类型为 `Hotkey`（`Rule.trigger: Hotkey`），两者是“字段名”与“类型名”的区别

### IR（平台无关）

> IR 的职责：只表达用户可观察的语义，不包含 Karabiner 的实现机制。

建议 IR 类型：

- `KeyCode`：如 `f18`, `h`, `1`, `left_arrow`
- `Modifier`（需要区分 left/right）：
  - 语义 modifier：`command/control/option/shift/fn/caps_lock`
  - 方向 modifier：`left_command/right_command/...`
- `Chord`（触发一步）：
  - `keys: List[KeyCode]`（>= 1；`>1` 表示 simultaneous keys）
  - `modifiers: Set[Modifier] = ∅`
- `Hotkey`（触发器）：
  - `steps: List[Chord]`（>= 1；`>1` 表示 sequence）
- `KeyChord`（动作要发出的按键）：
  - `key: KeyCode`
  - `modifiers: Set[Modifier] = ∅`
- `Action`（对外动作）：
  - `Emit(chord: KeyChord)`（当前阶段只需要这一种）
- `Rule`：
  - `trigger: Hotkey`
  - `action: Action`
  - `when: Context/Conditions = []`（可选：应用匹配、模式开关等“用户可见语义”）

### IR 示例

触发：`f18>w>v`，动作：`command+shift+option+1`

- `Hotkey(steps=[Chord(keys=[f18]), Chord(keys=[w]), Chord(keys=[v])])`
- `Action=Emit(KeyChord(key="1", modifiers={command,shift,option}))`

触发：`d+f`，动作：`left_command+left_control+l`

- `Hotkey(steps=[Chord(keys=[d,f])])`
- `Action=Emit(KeyChord(key="l", modifiers={left_command,left_control}))`

---

## 编译后端（IR → Karabiner JSON）

后端输入：`List[Rule]`（IR）

后端输出：Karabiner-Elements complex modifications `Rule(description, manipulators=[...])` 的 JSON

后端允许引入 Karabiner 专用机制（例如 `set_variable`），但不暴露给前端。

### Lowering：Chord

将 `Hotkey.steps` 只有一步的规则 lowering 为一个 manipulator：

- 如果 `Chord.keys` 长度为 1：
  - `from.key_code = keys[0]`
  - `from.modifiers = { mandatory: chord.modifiers, optional: ["any"] }`（后端默认；不进入配置文件）
- 如果 `Chord.keys` 长度 > 1：
  - `from.simultaneous = keys`
  - `from.modifiers` 同上
- 动作：
  - `to = [{ "key_code": action.key, "modifiers": [...] }]`

### Lowering：Sequence（默认策略：变量状态机）

默认策略由后端提供（前端不需要表达超时/取消等语义）。

核心思想：

- 为每个 sequence 维护“当前前缀状态”的 variable（状态机）
- 第一步进入 `seq_<root>_active = 1`
- 中间步骤在 `variable_if` 条件下推进到下一个前缀状态
- 最后一步清理状态并 emit 最终 key chord

关键点：

- 支持分叉：共享前缀（例如 `f18>w>v` 与 `f18>w>s`）
- 变量命名、reset、冲突规避均由后端负责（实现细节）

---

## 与现有配置的关系

当前 `keyboard.json` 使用 `f18>w>v` 这类 DSL，属于本设计中的 sequence 触发器。
后端应生成与 `origin.json/final.json` 类似的 Karabiner manipulators（内部使用 variable 状态机实现）。
