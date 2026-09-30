# Keysmith Switch 拓展包

[Keysmith Switch](https://github.com/Jia-Ethan/keysmith-switch) 的拓展包仓库。拓展包是一组**内容**（目前是提示词），可以在不更新 App 本身的情况下单独更新。

- 拓展包只包含数据，**没有任何可执行代码**。适配器仍随 App 发布。
- 每次发布是一个快照（清单加压缩包）；App 只信任写死的官方地址，来自那里才显示为“官方”。没有签名，所以 App 不会自动部署任何拓展包里的内容。
- App 默认离线；只有用户打开“拓展”后才会联网读取这个仓库。

格式见 [SPEC.md](SPEC.md)。

## 目录

```
packs/<包 id>/pack.json         描述文件
packs/<包 id>/prompts/*.md      提示词正文
scripts/                        校验、打包、封装
tests/                          格式测试
.github/workflows/              校验与发布
```

`packs/keysmith.example` 只是演示格式的示例包。

## 添加或修改一个包

```bash
# 1. 在 packs/<id>/ 下写 pack.json 和 prompts/*.md（sha256 可以先留空）
# 2. 自动填入哈希并校验
python3 scripts/seal.py packs/<id>
# 3. 全部检查
python3 -m unittest discover tests && python3 scripts/check.py
# 4. 试着打包并核对
python3 scripts/build.py --out dist
```

改内容后必须递增 `version`：同一个 `id` 和 `version` 不得改变内容。

## 发布

发布由 `release` 工作流完成，只能从 `main` 运行。

1. 合并 PR 到 `main`。
2. Actions → release → Run workflow，填快照标签 `YYYY.MM.DD.N`（例如 `2026.09.30.1`）。
3. 工作流先打包并核对，再创建 Release。
4. App 读取的地址：`https://github.com/Jia-Ethan/keysmith-switch-extensions/releases/latest/download/index.json`

建议（可选）：仓库 Settings → Environments → `production`，勾选 Required reviewers 加上自己，这样每次发布都需要你点一下批准。不设置也能发布，但任何有写权限的账号都能发布。

## 许可

尚未选择许可证。在选定之前，仓库内容保留所有权利；示例包仅用于演示格式。
