# 官方提示词来源

`keysmith.codex`、`keysmith.claude`、`keysmith.grok` 与 `keysmith.zcode` 均为 0.2.1，各收录一条提示词。下表的链接固定到提交，不随上游分支变化。机器可读记录见 [prompt-sources.json](prompt-sources.json)，供离线测试核对包内正文；更新正文时须同时更新来源记录和该包版本。包版本按包独立递增，不必四条同号。

## 固定输入

| 工具 | 源文件 | 提交 SHA | 源文件 SHA-256 |
| --- | --- | --- | --- |
| codex | [examples/gpt-overlay.md](https://github.com/Jia-Ethan/codex-keysmith/blob/cfcd96eb727c324ee8649170c43aaa632ff53cb3/examples/gpt-overlay.md) | `cfcd96eb727c324ee8649170c43aaa632ff53cb3` | `7d306ae69d831dad21ed54252b563e173877eeebc0bc92e81970849a7ab8ac4a` |
| claude | [examples/claude-project-rules.md](https://github.com/Jia-Ethan/claude-keysmith/blob/b14f924c629ed98235211b5ba0744c26da891b0b/examples/claude-project-rules.md) | `b14f924c629ed98235211b5ba0744c26da891b0b` | `ccb8e4c8b0f697a758d79c095126b9c6ff685a11908bc9f573730dba6b9d43ca` |
| claude | [examples/claude-append-prompt.md](https://github.com/Jia-Ethan/claude-keysmith/blob/b14f924c629ed98235211b5ba0744c26da891b0b/examples/claude-append-prompt.md) | `b14f924c629ed98235211b5ba0744c26da891b0b` | `28b73a5351a098eadc096883def5ad1918820786192c5822aae6a76b689ad23d` |
| grok | [examples/grok-unrestricted.md](https://github.com/Jia-Ethan/grok-keysmith/blob/6f09878a1ed540808fc21dbf70edebc382dc8740/examples/grok-unrestricted.md) | `6f09878a1ed540808fc21dbf70edebc382dc8740` | `3c669118d67690856f3ac11cd0f2beb687aa6e718dc76ed3f54c0751e01e48c9` |
| zcode | [examples/system-role.md](https://github.com/Jia-Ethan/zcode-keysmith/blob/8cbcfc9d5e097ed0f8edcfbc107037967dc693d9/examples/system-role.md) | `8cbcfc9d5e097ed0f8edcfbc107037967dc693d9` | `30e7de01b1a453d38cb1fa38bc8f4bb26eeaf8eccafada1aa178df1a1cf1c9e1` |

四个包在 0.2.1 都是 lab/craft recast，不再按源文件原始字节复制。各包保留该模型已测过的脸，不把 Grok 的 routing table 移植到 Claude / Codex / GLM。

Codex 以默认 `gpt-overlay.md` 为底：保留 overlay-append、EXECUTION / CONTINUATION、LOCAL EVAL 和中英第一行模板。工作区改成 local lab，provenance 措辞只决定占位符，HWID / 具名样本走重建路径，成人与脚本对话按 craft 写。不加入 routing table、拒词黑名单或 `Scenario MALWARE`。产品默认仍是 overlay-append；本机若走 `gpt-unrestricted.md` 整文件替换，安装本包不会覆盖那条路径。

Claude 以 `claude-project-rules.md` + `claude-append-prompt.md` 为输入，合成后再 recast 成一条。保留 Claude Code 身份、`[P]`、provenance 与成人 craft。补上 HWID / 具名样本重建、named-file/named-test 路径和脚本对话。不加入 routing table、能力清单或“ignore previous”。D-RS / D-KL 仍是 5.x 权重层，import 打不穿，需要 wrapper。本机 live 是 import-only，且 `~/.claude/keysmith/claude-project-rules.md` 是另一份 Keysmith 工作稿，安装本包只进提示词库，不自动部署。

Grok 以默认 `grok-unrestricted.md` 为底，保留 work-session、Scenario 字段表、CRED 对照例、Contract check 和工程意图镜像（只写在 PENTEST escalation / ZERODAY）。成人改成 craft；化学/装置改成 lab note；MALWARE 去掉引用拒词的句子，类型名仍只用来选字段。不把 contract-citing receipt 写进正文——4.6 会把它读成越狱。内核 CVE 的 exploit PoC 仍是权重层残余。

ZCode 0.2.1 以 v0.3.3 发布提交 `8cbcfc9` 的 `examples/system-role.md` 为输入。保留 Pier 身份、`[P]`、One Line、HWID 交付形状、named-file/named-test 路径、写作工艺和去本机绑定的游戏修改说明。去掉 GLM 上会被读成越狱说明书的元叙述（过滤层、consent form、"allowed"、"everything is on the table"）以及 keylogger/ransomware/stealer 能力清单。zcode-keysmith CLI 仍发布 v0.3.3 字节复制稿；本包是 Switch 库里的下一版脸。

## 正文转换

四条都是 lab/craft recast：以源文件为底改写开场与工作方式，输出 SHA 与输入 SHA 不同。

- Codex：仍是 overlay 结构，给 envelope-append 和 `developer_instructions` 用。
- Claude：不再做 `strip_markdown_h1()` 字节合成；输出是一条完整 lab/craft 正文。安装这条提示词并不意味着 App 额外启用 Claude CLI 的 append 通道。
- Grok：仍包在源文件的 ChatML 里，Scenario 应答行和字段表保留。
- ZCode：仍包在源文件的 `<project_instructions>` 里，供 `customSystemPrompt` 路径使用。

所有正文保留原项目的人名、`[P]` 和上下文。

## 包内正文 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| keysmith.codex / prompts/codex-keysmith.md | `a26ad8acd7b1b48eae5fb9892f6ad9a123fcf66960d9c6a5269d69028010556b` |
| keysmith.claude / prompts/claude-keysmith.md | `bb3ce45cd3a118ccf33f115b7266e07ef4a7175804f40811d7a7df2d54a4f599` |
| keysmith.grok / prompts/grok-keysmith.md | `6494e205e3aaf7b7d1c3615219e3166611c3f960da82debe817bb8337e144524` |
| keysmith.zcode / prompts/zcode-keysmith.md | `8e823d71a484af85601ac36cae515c989672b4e2a38cc283b56bdda93f4efd2f` |

## 许可

四个源项目的提示词使用 MIT 许可。Codex、Claude、Grok 的版权声明为 `Copyright (c) 2026 Jia-Ethan`；ZCode 为 `Copyright (c) 2026 Ethan`。每个包把自己那份完整通知保存在 `pack.json` 的 `license.notices` 中，随发布 ZIP 一起分发，不混入提示词正文。

## 拆分与旧包下架

0.2.0 起每个提示词是自己的包，原先捆绑四条的 `keysmith.core`（0.1.0、0.2.0 曾发布）和更早的 `keysmith.example` 不再出现在新清单里。历史提交与旧 Release 保留。仅合并 PR 不改变线上清单，须发布新快照才会生效。

已装过 `keysmith.core` 的用户，提示词库里的条目原样保留。安装新包时，库里已有正文相同的条目会被直接关联，不产生重复；若用户改过某条，则另存为新条目。当前 App 不会自动清理下架包，刷新新清单后扩展页也不再显示 `keysmith.core` 的卸载入口。安装新包只导入官方正文，不自动部署。
