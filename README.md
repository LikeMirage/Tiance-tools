# Tiance Tools

天策官方在线工具仓库。

仓库保存可公开分发的工具定义和程序文件。市场构建流程会校验每个工具、生成固定版本安装包，并发布统一的 `index.json`。

## 工具包结构

```text
tools/<tool-id>/
├─ manifest.json
├─ .tool/
│  ├─ tool.json
│  ├─ input.schema.json
│  ├─ output.schema.json
│  └─ examples.json
└─ program/
```

- `manifest.json`：市场身份、版本、作者、许可证和兼容范围。
- `.tool/tool.json`：调用名称、展示名称、用途和运行方式。
- `program/`：工具运行程序及发布者决定公开的配置模板。

## 收录要求

- 工具目录名必须与 `manifest.json.id` 一致。
- 每个版本必须使用符合语义化版本格式的明确版本号。
- 工具调用名称必须使用小写字母、数字和下划线，并以小写字母开头。
- 不得包含 `.Tiance`、`dependencies`、`.git`、`__pycache__` 或 `.pyc` 等本地状态和依赖缓存。
- 发布者对公开内容负责。提交前必须自行清除 API Key、Token、密码等秘密；需要用户填写的配置应只保留字段结构或示例占位值。

天策安装时由用户选择自己的本地工具分类。调用名称冲突会在安装弹窗中提示并允许改名，市场身份始终由 `manifest.json.id` 标识。

## 许可证

仓库内容采用 [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)。

