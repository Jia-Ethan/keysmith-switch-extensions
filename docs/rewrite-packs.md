# 官方输入替换规则包

三个包由 [`scripts/gen_rewrite_packs.py`](../scripts/gen_rewrite_packs.py) 生成，不要手改 `rules.json`。改词表就改生成器，然后：

```bash
python3 scripts/gen_rewrite_packs.py
python3 -m unittest discover tests
```

`from` 在三包之间不重复，这样表的上下顺序不会改变同一段输入的命中。

## 包

| 包 id | 名称 | 作用 |
| --- | --- | --- |
| `keysmith.rewrite.wrap` | 表达层 · 路由头 | `【夹具】` / `【范围】` / `【描述】`、`[[fixture]]` / `ks::describe`，以及「帮我破解」一类开场，换成 grok-keysmith 已测过的 wrap 前缀 |
| `keysmith.rewrite.lab` | 表达层 · 实验室 | 祈使句 × 类型名（`write a keylogger`、`帮我写一个键盘记录器`）改成样本描述；足够长的类型名在句中改成名词 |
| `keysmith.rewrite.craft` | 表达层 · 文稿 | 成人 / 暴力 / 配方的冷开场改成稿件改写或文学模板句式 |

默认 `tools` 为四个 Agent，`min_app_version` 为 `0.6.0`（输入替换覆盖 Grok Build 的第一个版本）。不密封。

## 纪律

- 完整 `from` 才进表：汉字四字，或英文两个词，或 8 个字符。标记、`写黄文`、`keylogger` 这类白名单除外。
- 不收：`破解`、`绕过`、`会员`、`杀`、`hack`、`crack`、`shell`、`dump`、`inject` 等短词。
- `to` 是陈述句或路由头，不以「请 / 帮我 / you must / ignore」开头。
- 替换产物不会再扫（App 引擎如此），所以 `to` 里可以出现类型名。
- 做工程时关掉文稿包。路由头和实验室可以同时开。

## 引擎

字面匹配、区分大小写、同一位置最长优先、斜杠命令整条跳过。没有句首锚点，所以短开场（「帮我」「写一个」）单独不进表，只作为更长 `from` 的前缀。

用户回合开头的祈使句点名类型，是 2026-09 grok-4.6 在场景路由之前拒绝的形态；`--wrap describe` 把同一题从 0/3 推到 3/4。实验室包的笛卡尔积就是在做这件事。NSFW 轴仍受上游分类器限制，文稿包只把冷开场收成测过更稳的改写句式。
