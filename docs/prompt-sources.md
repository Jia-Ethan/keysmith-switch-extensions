# 官方提示词来源

`keysmith.core` 0.1.0 收录四个 Keysmith 项目的已提交提示词。下表的链接固定到提交，不随上游分支变化。机器可读记录见 [prompt-sources.json](prompt-sources.json)，供离线测试核对包内正文；更新正文时须同时更新来源记录和包版本。

## 固定输入

| 工具 | 源文件 | 提交 SHA | 源文件 SHA-256 |
| --- | --- | --- | --- |
| codex | [examples/gpt-overlay.md](https://github.com/Jia-Ethan/codex-keysmith/blob/cfcd96eb727c324ee8649170c43aaa632ff53cb3/examples/gpt-overlay.md) | `cfcd96eb727c324ee8649170c43aaa632ff53cb3` | `7d306ae69d831dad21ed54252b563e173877eeebc0bc92e81970849a7ab8ac4a` |
| claude | [examples/claude-project-rules.md](https://github.com/Jia-Ethan/claude-keysmith/blob/977fa2f867ef7b91c02cabfb83509b7279b5285e/examples/claude-project-rules.md) | `977fa2f867ef7b91c02cabfb83509b7279b5285e` | `d15aa6b25ee39b672abe79e215d9731bd083b48b57c4a5aad2e07a37dc09c94e` |
| claude | [examples/claude-append-prompt.md](https://github.com/Jia-Ethan/claude-keysmith/blob/977fa2f867ef7b91c02cabfb83509b7279b5285e/examples/claude-append-prompt.md) | `977fa2f867ef7b91c02cabfb83509b7279b5285e` | `e41a0f41d607d792ccfef233e768df1ce5c565b6e21b07f62bad8a90d119e76b` |
| grok | [examples/grok-unrestricted.md](https://github.com/Jia-Ethan/grok-keysmith/blob/6f09878a1ed540808fc21dbf70edebc382dc8740/examples/grok-unrestricted.md) | `6f09878a1ed540808fc21dbf70edebc382dc8740` | `3c669118d67690856f3ac11cd0f2beb687aa6e718dc76ed3f54c0751e01e48c9` |
| zcode | [examples/system-role.md](https://github.com/Jia-Ethan/zcode-keysmith/blob/8cbcfc9d5e097ed0f8edcfbc107037967dc693d9/examples/system-role.md) | `8cbcfc9d5e097ed0f8edcfbc107037967dc693d9` | `30e7de01b1a453d38cb1fa38bc8f4bb26eeaf8eccafada1aa178df1a1cf1c9e1` |

Codex 使用默认的 `gpt-overlay.md`，Grok 使用默认的 `grok-unrestricted.md`。ZCode 使用干净的 v0.3.3 发布工作树对应提交，未纳入本地未提交稿。Claude 和 Grok 固定到本次核验的已提交来源；这两份提示词与调研时远端主分支的对应正文一致。

## 正文转换

Codex、Grok、ZCode 按源文件原始字节复制，包括源文件自身的结构标记。所有正文保留原项目的人名、`[P]` 和上下文；这次迁入未将它们改写为通用人格。

Claude 合成一条。转换与原项目的 `strip_markdown_h1()` 及正文拼接规则一致：

1. 主规则按 `splitlines()` 拆行；若第一行左侧去空白后以 `# ` 开头，去掉该行，剩余行用 LF 连接并去掉开头的换行。
2. 对主规则执行 `rstrip()`，对 append 执行 `strip()`。
3. 输出 `主规则 + "\n\n" + append + "\n"`，以 UTF-8 编码。

仅合成正文，不加入 agent 的 YAML frontmatter 或部署所有权标记。安装这条提示词并不意味着 App 额外启用 Claude CLI 的 append 通道。

## 包内正文 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| prompts/codex-keysmith.md | `7d306ae69d831dad21ed54252b563e173877eeebc0bc92e81970849a7ab8ac4a` |
| prompts/claude-keysmith.md | `b6e4ae27e7a5f2b1c564710f1bad6f5c22a9367aed09c889d1be3ce27f5438e2` |
| prompts/grok-keysmith.md | `3c669118d67690856f3ac11cd0f2beb687aa6e718dc76ed3f54c0751e01e48c9` |
| prompts/zcode-keysmith.md | `30e7de01b1a453d38cb1fa38bc8f4bb26eeaf8eccafada1aa178df1a1cf1c9e1` |

## 许可

四个源项目的提示词使用 MIT 许可。Codex、Claude、Grok 的版权声明为 `Copyright (c) 2026 Jia-Ethan`；ZCode 为 `Copyright (c) 2026 Ethan`。两份完整通知保存在包的 `pack.json` 的 `license.notices` 中，随发布 ZIP 一起分发，不混入提示词正文。

## 旧示例下架

新版发布清单移除 `keysmith.example`，替换为 `keysmith.core`。历史提交与旧 Release 保留。仅合并 PR 不改变线上清单，须发布新快照才会生效。

已有用户的旧示例仍留在本地提示词库，可自行删除；当前 App 不会自动清理下架包，刷新新清单后扩展页也不再显示旧包的卸载入口。安装新包只导入官方正文，不自动部署。
