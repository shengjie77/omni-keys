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
  - `keys: List[KeyCode]`（>= 1）
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
  - `when: Context/Conditions = []`（可选：应用匹配等“用户可见语义”）

### IR 示例

触发：`f18>w>v`，动作：`command+shift+option+1`

- `Hotkey(steps=[Chord(keys=[f18]), Chord(keys=[w]), Chord(keys=[v])])`
- `Action=Emit(KeyChord(key="1", modifiers={command,shift,option}))`

触发：`leader_key+h`，动作：`left_arrow`

- `Hotkey(steps=[Chord(keys=[f18,h])])`
- `Action=Emit(KeyChord(key="left_arrow", modifiers=∅))`

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
- 如果 `Chord.keys` 长度为 2 且其中一个是 leader：
  - 作为 **leader hold chord** 处理（条件 `leader_hold==1`，`from.key_code=另一键`）
- 其他多键 chord：当前不支持
- 动作：
  - `to = [{ "key_code": action.key, "modifiers": [...] }]`

### Lowering：Sequence（单 leader + hold/seq 双变量）

默认策略由后端提供（前端不需要表达超时/取消等语义）。

核心思想：使用两个变量，职责清晰、冲突少。

- `omni.hold`（int）：leader 物理按住标记（1/0）
- `omni.seq`（string）：序列状态（`seq:<leader>` / `seq:<leader>:<prefix...>` / `idle`）

#### Leader 行为（持按与轻点）

> 目标：按住 leader 可连续触发，轻点 leader 进入序列模式；并允许“按得很快”时序列不中断。

规则：

- leader **按下**：`omni.hold = 1`
- leader **抬起**：`omni.hold = 0`
- leader **轻点**：`to_if_alone` 设置 `omni.seq = seq:<leader>`

#### hold 下的 chord（连续触发）

当 `omni.hold == 1` 时，按任意配置的键触发动作，但 **不改变状态**，以支持连续按键：

- 条件：`variable_if omni.hold == 1`
- 动作：`to` 发出目标按键（不写入状态）

#### 序列推进与最终触发

以 `leader>f>t` 为例：

- `omni.seq == seq:<leader>` + `f` → `omni.seq = seq:<leader>:f`
- `omni.seq == seq:<leader>:f` + `t` → 触发动作 + `omni.seq = idle`

为避免“leader 尚未抬起就按下一键”导致序列丢失，可允许从 hold 直接进入序列：

- `omni.hold == 1` + `f` → `omni.seq = seq:<leader>:f`

#### 分叉序列

例如 `leader>w>v` 与 `leader>w>s`：

- `seq:<leader>` + `w` → `seq:<leader>:w`
- `seq:<leader>:w` + `v` → emit + `idle`
- `seq:<leader>:w` + `s` → emit + `idle`

#### 取消与超时

- **按错键**：当 `omni.seq` 为 `seq:*` 时，任意非期望键 → `omni.seq = idle`
- **超时**：进入 `seq:*` 后加 `to_delayed_action`，超时统一回 `idle`

超时默认值：

- `basic.to_delayed_action_delay_milliseconds = 1000`
- 触发时使用 `to_delayed_action.to_if_invoked` 写入 `idle`

关键点：

- 只用一个 leader key，逻辑仍清晰
- `hold` 与 `seq` 解耦，降低冲突与误触
- 允许 hold 直接推进序列，避免“按得太快”失效

---

## 与现有配置的关系

当前 `shortcut.toml` / `shortcut.json` 使用 `leader_key>w>v` 这类 DSL，属于本设计中的 sequence 触发器。
后端应生成与 `shortcut.json` 类似的 Karabiner manipulators（内部使用 variable 状态机实现）。
