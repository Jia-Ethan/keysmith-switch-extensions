# 拓展包格式（schema 1）

本文件是 Keysmith Switch 拓展包的格式规定。仓库里的 `scripts/packlib.py` 按这些规则校验，App 安装时会**再校验一遍**：来源再可信，内容是否合格也只能靠逐项检查。

## 1. 发布物

每次发布一个“快照”，是 GitHub Release 的一组文件：

| 文件 | 作用 |
| --- | --- |
| `index.json` | 所有拓展包的清单，见 §3 |
| `<包 id>-<版本>.zip` | 每个拓展包一个压缩包 |

清单里写着每个压缩包的 `sha256` 和大小。链条是 **固定的官方地址 → 清单 → 哈希 → 压缩包**。

压缩包地址写成快照自己的固定地址（`releases/download/<tag>/…`），不是 `latest`，所以清单和压缩包永远配套。App 只接受官方地址之下的压缩包地址。

## 2. 拓展包（`packs/<id>/`）

```
packs/keysmith.claude/
  pack.json
  prompts/
    claude-keysmith.md
```

`pack.json`：

| 字段 | 规则 |
| --- | --- |
| `schema` | 固定为 `1` |
| `id` | 小写字母、数字、`.`、`-`，最长 64；必须与目录名一致 |
| `version` | 三段式 `x.y.z` |
| `min_app_version` | 三段式；低于此版本的 App 不显示、不安装 |
| `kind` | `prompts`（提示词包）、`rules`（输入替换规则包，见 §2.1）或 `harness`（Agent 组件包，见 §2.2） |
| `name`、`description` | 对象，键为 `zh-CN`、`zh-TW`、`en`，至少一种语言，不能为空。`description` 仍是 schema 1 的必填字段，但**不进入 App 拓展页卡片**，见下方“拓展页展示规则” |
| `tools` | 适用的 Agent：`claude`、`codex`、`grok`、`zcode`、`pi`、`dsh` 中的若干个，不重复。含 `pi` 的包 `min_app_version` 至少 `0.7.0`（第一个把 pi 列为 Agent 的 App）；含 `dsh` 的包至少 `0.8.1`（第一个把 DSH 列为 Agent 的 App）。更早的 App 会把这样的包列为「需要新版 App」 |
| `items` | 1 到 200 条，见下 |
| `license` | 可选对象：`spdx` 为许可标识，`notices` 为完整版权与许可通知的字符串数组；随 `pack.json` 分发，不属于提示词正文 |

### 拓展页展示规则

**拓展页卡片不展示包摘要（`description`）。** 卡片只显示名称、官方角标、条数、大小、版本和安装状态。这条规则对已上架、已安装和以后发布的所有包一律适用，不针对某一个包。

- 写包：`description` 照常填写（schema 仍要求），但它不会出现在卡片上，不要指望靠它向用户传达信息，也不要为了卡片去改写它。
- 审 PR：新增或修改包时，不接受“让摘要在卡片上显示”的改动；不要求为了界面去清空或改写已有的 `description`。
- 发快照：发布说明里不承诺摘要展示；快照对应的 App 版本必须遵守本规则。
- 清单 `index.json` 仍携带 `description`，这是格式的一部分，与展示无关。

`license` 是 schema 1 的可选描述元数据。现有 App 忽略不认识的字段；增加此字段不改变安装、工具适配或来源信任规则。

`items[]`：

| 字段 | 规则 |
| --- | --- |
| `id` | 小写字母、数字、`-`；包内唯一 |
| `tool` | 必须在包的 `tools` 里 |
| `title` | 同 `name` 的规则 |
| `tags` | 可选，最多 8 个，每个最长 24 字符 |
| `file` | `prompts/` 下的 `.md` 文件，包内唯一 |
| `sha256` | 该文件内容的 SHA-256（小写十六进制） |

文件规则：UTF-8、非空、单个不超过 256 KiB，整个包解压后合计不超过 4 MiB，压缩包本身不超过 2 MiB；不允许符号链接；**目录里不允许出现 `pack.json` 没有列出的文件**，防止夹带内容。路径只能是相对路径，不能含 `..`、反斜杠、空段。

提示词文件只有正文，不带任何元数据；标题和标签在 `pack.json` 里。这与 App 交给适配器的内容一致。

### 2.1 规则包（`kind: "rules"`）

规则包给 App 的「输入替换」新增一张**只读**规则表：用户在 Agent 里打字，发给模型前按表做字面替换。它不写入提示词库。

```
packs/example.rules/
  pack.json
  rules.json
```

`pack.json` 与 §2 相同，以下几处不同：

| 字段 | 规则 |
| --- | --- |
| `min_app_version` | `tools` 正好是 `["codex"]` 时至少 `0.4.0`；其他任何组合至少 `0.5.0`（第一个支持 Claude Code、ZCode 输入替换的 App；0.4.0 不会列出这样的包）。`opaque` 为 `true` 时至少 `0.6.5`（第一个把规则正文从界面拿掉的 App；更早的版本把这样的包列为「需要新版 App」，不能安装） |
| `tools` | 规则表默认作用于哪些 Agent，取值同 §2 里已接输入替换的那些：`claude`、`codex`、`grok`、`zcode`，不重复。这四个都写表示「全部已接输入替换的 Agent」。`pi` 和 `dsh` 目前没有输入替换，官方规则包不要把它们写进 `tools`。安装后用户可以在 App 里收窄或放宽，包更新时保留用户的选择 |
| `opaque` | 可选布尔值，默认 `false`。为 `true` 时这是一张**密封**规则表：App 安装、列表、更新确认都不展示 `from` / `to`，也没有「复制到我的规则」。密封只管界面，**不是加密**：发布的 zip 里 `rules.json` 仍是明文，任何人都能下载；安装后规则在本机数据库、备份和中转服务读取的 `rules.json` 里也是明文。不要把需要保密的内容写进规则包。提示词包不得带这个字段 |
| `items` | **不允许出现** |
| `rules` | 对象，只有 `file` 和 `sha256` 两个键。`file` 固定为 `rules.json`，`sha256` 是该文件内容的 SHA-256 |

`rules.json`：

```json
{ "rules": [ { "from": "要匹配的文字", "to": "替换为" } ] }
```

| 规则 | 说明 |
| --- | --- |
| 结构 | 顶层只有 `rules`；每条只有 `from` 和 `to`，都是字符串 |
| 条数 | 1 到 1000 条 |
| `from` | 非空，最长 200 个字符，不能含控制字符（含换行、制表符），包内不重复 |
| `to` | 最长 2000 个字符，可以为空（表示删除），可以含换行 |

这些规则与 App 里用户自己填写规则时的检查完全相同。App 安装时用同一套代码再校验一遍。

匹配语义（由 App 执行，写包时需要知道）：

- 字面匹配，区分大小写，不做 Unicode 归一化。
- 从左到右扫描，同一位置取最长的那条；替换后的文字不会再被替换。
- 以 `/` 开头的消息（忽略前导空白）是斜杠命令，整条跳过。
- 只改用户自己输入的文字；助手回复、工具输出、Agent 自带的上下文（例如 Claude Code 的 `<system-reminder>`）不改。斜杠命令展开后的内容也不改。

安装与更新（App 的行为）：

- 安装前，App 先把整张规则表展示给用户，用户可以选「安装并启用」或「只安装」。**密封包**（`opaque: true`）只展示名称、条数和适用的 Agent，不展示 `from` / `to`。
- **已启用**的规则表有新版本时，不会自动生效：新版本先挂起，用户在「输入替换」页看到新增、删除、改动的差异，确认后才切换。密封包的更新只展示版本号和条数，不展示差异正文。
- **未启用**的规则表直接跟随新版本，包括从普通包变成密封包。
- 已启用的表从普通包变成密封包时，更新确认同样只展示版本号和条数。
- 规则包是只读的；用户想改，复制到「我的规则」再改。密封包没有这项操作。

默认的官方快照**不包含**任何规则包。规则内容由包作者自行决定，不随 App 内置。

### 2.2 组件包（`kind: "harness"`）

组件包装的不是提示词，而是 **Agent 自己的组件**：技能、斜杠命令、子 Agent、附加规则文件。App 把它们写进各家 Agent 自己的目录，记下写了哪些文件，卸载时只删自己写的、没被改过的文件。

这一版只有**第 1 层**（`tier: 1`）：装上以后**不会运行任何代码**。hook、MCP、状态栏、插件、权限、环境变量这些会运行代码或放宽权限的东西属于第 2 层，不在格式里，校验器一律拒绝。

> [!IMPORTANT]
> 第 1 层只保证"装上不跑代码"，不等于"无害"：纯文本技能也可以叫模型去执行危险命令。这一点靠人工审核挡。

```
packs/example.review-kit/
  pack.json
  components/
    review-diff/SKILL.md          技能（目录，可以有多个 .md）
    review-diff/checklist.md
    review.md                     斜杠命令
    reviewer.md                   子 Agent
    house-style.md                附加规则
```

`pack.json` 与 §2 相同，以下几处不同：

| 字段 | 规则 |
| --- | --- |
| `min_app_version` | 至少 `0.9.0`（第一个能安装组件包的 App） |
| `tools` | `claude`、`codex`、`grok` 中的若干个。ZCode、pi、DSH 的落点还没核实完，暂不接受。每个写在这里的 Agent 至少要有一个组件 |
| `tier` | 必填，只能是 `1` |
| `components` | 1 到 50 个组件，见下 |
| `items`、`rules` | **不允许出现**。反过来，提示词包和规则包也不能带 `tier`、`components` |

`components[]`：

| 字段 | 规则 |
| --- | --- |
| `id` | 小写字母、数字、`-`；包内唯一。决定文件位置，见下 |
| `type` | `skill`、`command`、`agent`、`rule` 之一 |
| `name` | 用户看到、调用的名字（`/name`、子 Agent 名、规则文件名）。小写字母开头，只含小写字母、数字、`-`，最长 40。`ks-` 和 `keysmith` 开头的只留给官方包（`keysmith.` 开头的 id）。技能和命令都用 `/name` 调用，所以同一个包里技能和命令不能同名。不能和受支持 Agent 的内置斜杠命令、内置子 Agent 同名（列表见 `scripts/packlib.py`） |
| `tools` | 包 `tools` 的子集，不重复，而且这种组件在那个 Agent 上要有落点（见下表）。例如 Codex 没有斜杠命令和规则文件 |
| `title` | 同 `name` 的本地化规则 |
| `files` | 文件列表，每项只有 `path` 和 `sha256` |

文件位置：

- `skill`：全部文件放在 `components/<id>/` 下，最多 20 个，其中必须有 `components/<id>/SKILL.md`；子目录里不能再出现 `SKILL.md`。
- `command`、`agent`、`rule`：正好一个文件，`components/<id>.md`。
- 只允许 `.md`；同一个路径（不区分大小写）不能被两个组件用。
- 路径的每一段只能用 ASCII 字母、数字、`.`、`_`、`-`，不以 `.` 结尾，也不能是 Windows 的设备名（`con`、`aux`、`nul`、`com1` 等）。原因是 APFS 和 NTFS 不区分大小写，APFS 还会把 `ſ` 当成 `s`、把 `K`（开尔文）当成 `K`，并把 NFD 和 NFC 当成同一个名字：看起来不同的两个文件名，写到磁盘上可能是同一个文件，后写的会盖掉先检查过的那个。组件 `name` 同样不能是这些设备名。其余文件规则同 §2：UTF-8、非空、大小上限、不允许符号链接、目录里不能有清单外的文件。

正文规则（App 写入前用同一套代码再查一遍）：

- 只用 LF 换行；不能有控制字符（制表符、换行除外）；不能有会隐藏或重排文字的不可见字符（双向控制符、零宽字符、BOM、Unicode tag 字符）。审核者看到的必须就是模型读到的。
- 不能有 `` !`命令` `` 或以 `!` 开头的代码块（```` ```! ````）：Claude Code 调用技能、命令时会把它们当 shell 执行，那就是第 2 层。
- 不能有引用项目以外文件的 `@`：`@~/`、`@/`、`@$`、`@..`。

**frontmatter 是白名单。** 有任何不在表里的键，就拒绝：

| 组件 | 允许的键 | 必须有的键 | 说明 |
| --- | --- | --- | --- |
| `skill` | `name`、`description` | 两个都要 | `name` 等于组件的 `name`。`allowed-tools`、`hooks`、`model`、`context`、`agent` 等会放宽权限或改运行方式，拒绝 |
| `command` | `description`、`argument-hint` | 无，也可以没有 frontmatter | `allowed-tools` 会放宽权限，拒绝 |
| `agent` | `name`、`description` | 两个都要 | `name` 等于组件的 `name`。`tools`、`model`、`permissionMode`、`mcpServers`、`hooks` 拒绝。正文就是这个子 Agent 的指令 |
| `rule` | 无 | — | 不能有 frontmatter |

frontmatter 只接受一个严格的子集，避免"看起来是这样，YAML 读出来是那样"：

- 第一行正好是 `---`，结束行正好是 `---`。
- 中间每行是 `key: value`，冒号后是空格，值写在同一行。不支持列表、嵌套、多行、注释、锚点、标签。
- 值是普通文字，或一对 `"…"` / `'…'` 括起来的文字（引号里不能再出现同种引号，双引号里不能有 `\`）。会被 YAML 读成别的东西的普通值（`yes`、`no`、`null`、数字、以 `[` `{` `|` `>` `&` `*` `!` `-` 等开头的、含 `: ` 或 ` #` 的）必须加双引号。
- frontmatter 之后必须有正文。
- 装给 Codex 的子 Agent，正文里不能出现 `'''`（App 把正文写成 TOML 多行字面量字符串）。

各 Agent 的落点（App 0.9.0 的行为；根目录遵守 `CLAUDE_CONFIG_DIR`、`CODEX_HOME`、`GROK_HOME` 和 App 的隔离 home 设置）：

| 组件 | Claude Code | Codex | Grok Build |
| --- | --- | --- | --- |
| `skill` | `~/.claude/skills/<name>/` | `~/.agents/skills/<name>/`（共享目录，ZCode、pi、DSH 也会读到，App 安装前会说明） | `~/.grok/skills/<name>/` |
| `command` | `~/.claude/commands/<name>.md` | 不支持 | `~/.grok/commands/<name>.md` |
| `agent` | `~/.claude/agents/<name>.md` | `~/.codex/agents/<name>.toml`（App 转换：`name`、`description`，正文写成 `developer_instructions`） | `~/.grok/agents/<name>.md` |
| `rule` | `~/.claude/rules/<name>.md` | 不支持 | `~/.grok/rules/60-<name>.md` |

技能目录里的文件按它在 `components/<id>/` 下的相对路径放。

安装、卸载与更新（App 的行为）：

- 安装前逐个文件展示**落点和完整内容**，用户确认后才写。
- 目标位置已经有**不是 App 写的**文件或目录，就是冲突，直接拦下，告诉用户是哪个文件；不提供覆盖。
- App 在台账里记下每个写入的文件和写入时的 `sha256`。卸载只删台账里、而且内容没变的文件；用户改过的保留，并说明。
- 已安装的组件包有新版本时**不会自动生效**：新版本先挂起，逐个文件展示差异，用户确认后才切换。
- 组件包不碰提示词部署管的任何文件（`CLAUDE.md` 托管块、`model_instructions_file`、`99-keysmith.md` 等），两边互不影响。
- 0.9.0 以前的 App 遇到 `kind: "harness"` 会跳过这一条，不显示，也不影响其他包。

## 3. 清单 `index.json`

```json
{
  "schema": 1,
  "generated_at": "2026-09-30T00:00:00Z",
  "packs": [
    {
      "id": "keysmith.claude",
      "version": "0.2.0",
      "min_app_version": "0.2.5",
      "kind": "prompts",
      "name": { "zh-CN": "Claude Keysmith" },
      "description": { "zh-CN": "Claude Keysmith 项目的主提示词" },
      "tools": ["claude"],
      "item_count": 1,
      "url": "https://github.com/…/releases/download/2026.09.30.1/keysmith.claude-0.2.0.zip",
      "sha256": "…",
      "size": 19339
    }
  ]
}
```

规则包的条目同样写在 `packs` 里，`kind` 为 `rules`，`tools` 与 `pack.json` 一致，`item_count` 为 `0`；其余字段相同。密封包额外带 `"opaque": true`；非密封包不写这个字段。

组件包的条目 `kind` 为 `harness`，`item_count` 为 `0`，另带 `tier` 和 `components`。`components` 每项只有 `id`、`type`、`name`、`tools`、`title`，不带文件和哈希；内容以压缩包为准。

写出方式固定（键排序、两空格缩进、末尾换行、UTF-8），同样的内容总是同样的字节。

**清单里没有"官方"之类的字段，有意如此。** 官方与否只由"从哪个地址取到的"决定，任何文件里的自我声明都不算数。

## 4. 信任

- **没有签名。** 信任的是地址：官方源是写死在 App 里的 HTTPS 地址，只有它之下的内容算“官方”。
- 这意味着：如果发布者的 GitHub 账号或仓库被入侵，对方可以发布提示词。所以 App 对拓展包的限制很严：只写入提示词库、**从不自动部署**，部署前仍要用户确认。
- 组件包直接写进 Agent 的目录，所以格式上只收第 1 层（不运行代码），frontmatter 只收白名单里的键；安装前展示每个文件的落点和完整内容，更新必须用户确认，卸载只删 App 写的、没被改过的文件。
- 规则包一旦启用就会影响发给模型的内容，所以限制更严：安装前先展示全部规则；已启用的表有更新时必须用户确认才切换。密封包例外：用户安装和确认更新时看不到规则正文，等于把「改了什么」交给发布者，信任根仍是写死的官方地址。正文本身并不保密（见 §2.1 `opaque`）。
- 将来支持第三方来源时，每个来源是它自己的地址，界面显示“非官方”。

## 5. App 安装时必须做的事

1. 只在用户主动打开"拓展"后联网。
2. 取 `index.json`，格式不对就整个丢弃，不显示任何内容。
3. 检查 `min_app_version` 和 `schema`；不认识的直接忽略，不报错。
4. 下载压缩包，先核对大小和 `sha256`，再解压。解压时不信任压缩包里的任何路径，逐项按 §2 重新校验。
5. 提示词包只写入提示词库，**从不自动部署**。库里被用户改过的条目，更新时不覆盖，另存为新条目。
6. 规则包写入只读规则表，规则见 §2.1。索引里的 `kind` 必须与压缩包里 `pack.json` 的 `kind` 一致。
7. 组件包按 §2.2 写入 Agent 目录：先展示、再确认、写台账；目标位置有别人的文件就拦下。

## 6. 版本与兼容

- 格式变更递增 `schema`。App 遇到更高的 `schema` 就忽略，不会因此崩溃。
- 拓展包的 `version` 只增不减；同一个 `id` 和 `version` 的内容不得改变。
- 新增字段必须向后兼容；App 忽略不认识的字段。
