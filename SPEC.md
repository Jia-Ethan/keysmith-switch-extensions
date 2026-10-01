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
packs/keysmith.core/
  pack.json
  prompts/
    codex-keysmith.md
    claude-keysmith.md
    grok-keysmith.md
    zcode-keysmith.md
```

`pack.json`：

| 字段 | 规则 |
| --- | --- |
| `schema` | 固定为 `1` |
| `id` | 小写字母、数字、`.`、`-`，最长 64；必须与目录名一致 |
| `version` | 三段式 `x.y.z` |
| `min_app_version` | 三段式；低于此版本的 App 不显示、不安装 |
| `kind` | 目前只有 `prompts` |
| `name`、`description` | 对象，键为 `zh-CN`、`zh-TW`、`en`，至少一种语言，不能为空 |
| `tools` | 适用的 Agent：`claude`、`codex`、`grok`、`zcode` 中的若干个，不重复 |
| `items` | 1 到 200 条，见下 |
| `license` | 可选对象：`spdx` 为许可标识，`notices` 为完整版权与许可通知的字符串数组；随 `pack.json` 分发，不属于提示词正文 |

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

## 3. 清单 `index.json`

```json
{
  "schema": 1,
  "generated_at": "2026-09-30T00:00:00Z",
  "packs": [
    {
      "id": "keysmith.core",
      "version": "0.1.0",
      "min_app_version": "0.2.5",
      "kind": "prompts",
      "name": { "zh-CN": "Keysmith 官方提示词" },
      "description": { "zh-CN": "四个 Keysmith 子项目的官方提示词" },
      "tools": ["codex", "claude", "grok", "zcode"],
      "item_count": 4,
      "url": "https://github.com/…/releases/download/2026.09.30.1/keysmith.core-0.1.0.zip",
      "sha256": "…",
      "size": 19339
    }
  ]
}
```

写出方式固定（键排序、两空格缩进、末尾换行、UTF-8），同样的内容总是同样的字节。

**清单里没有"官方"之类的字段，有意如此。** 官方与否只由"从哪个地址取到的"决定，任何文件里的自我声明都不算数。

## 4. 信任

- **没有签名。** 信任的是地址：官方源是写死在 App 里的 HTTPS 地址，只有它之下的内容算“官方”。
- 这意味着：如果发布者的 GitHub 账号或仓库被入侵，对方可以发布提示词。所以 App 对拓展包的限制很严：只写入提示词库、**从不自动部署**，部署前仍要用户确认。
- 将来支持第三方来源时，每个来源是它自己的地址，界面显示“非官方”。

## 5. App 安装时必须做的事

1. 只在用户主动打开"拓展"后联网。
2. 取 `index.json`，格式不对就整个丢弃，不显示任何内容。
3. 检查 `min_app_version` 和 `schema`；不认识的直接忽略，不报错。
4. 下载压缩包，先核对大小和 `sha256`，再解压。解压时不信任压缩包里的任何路径，逐项按 §2 重新校验。
5. 只写入提示词库，**从不自动部署**。库里被用户改过的条目，更新时不覆盖，另存为新条目。

## 6. 版本与兼容

- 格式变更递增 `schema`。App 遇到更高的 `schema` 就忽略，不会因此崩溃。
- 拓展包的 `version` 只增不减；同一个 `id` 和 `version` 的内容不得改变。
- 新增字段必须向后兼容；App 忽略不认识的字段。
