# Keysmith Switch 拓展包

[Keysmith Switch](https://github.com/Jia-Ethan/keysmith-switch) 的拓展包仓库。拓展包是一组**内容**（目前是提示词），可以在不更新 App 本身的情况下单独更新。

- 拓展包只包含数据，**没有任何可执行代码**。适配器仍随 App 发布。
- 每次发布是一个带签名的快照；App 用内置公钥验证，验证通过才显示为“官方”。
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

发布由 `release` 工作流完成，只能从 `main` 运行，并需要 `production` 环境的审批。

1. 合并 PR 到 `main`。
2. Actions → release → Run workflow，填快照标签 `YYYY.MM.DD.N`（例如 `2026.09.30.1`）。
3. 工作流先打包，再停在审批；审批通过后才用签名密钥签名并创建 Release。
4. App 读取的地址：`https://github.com/Jia-Ethan/keysmith-switch-extensions/releases/latest/download/index.json`

## 首次设置（仓库管理员）

签名密钥由管理员自己生成，**私钥不要发给任何人，也不要放进仓库**。

1. 生成拓展包专用密钥（不要复用 App 更新的密钥）：

   ```bash
   npx @tauri-apps/cli@2.11.4 signer generate -w ~/.keysmith-extensions-signing.key
   ```

   设一个密码，妥善保存私钥文件和密码。输出的公钥交给 App 内置。
2. 仓库 Settings → Environments → 新建 `production`，勾选 Required reviewers，加上自己。
3. 在 `production` 环境里添加两个 Secret：
   - `EXT_SIGNING_PRIVATE_KEY`：私钥文件的全部内容
   - `EXT_SIGNING_PASSWORD`：私钥密码
4. 建议给 `main` 开分支保护，要求 PR 和 CI 通过。

## 许可

尚未选择许可证。在选定之前，仓库内容保留所有权利；示例包仅用于演示格式。
