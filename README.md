# Tiance Tools

天策官方在线工具仓库。

仓库保存可公开分发的工具定义和程序文件。市场构建流程会校验每个工具、生成固定版本安装包，并发布统一的 `index.json`。

## GUI 桌面操作工具

建议使用 **天策 0.3.28 或更新版本、Windows 10/11**。GUI 系列包含以下七个工具：

| 调用名 | 用途 |
|---|---|
| `gui_runtime` | 输入锁与运行器；必须先 start 并等待成功 |
| `gui_inspect` | 窗口/屏幕截图、树状递归网格、返回已有视图与网格叠加层切换 |
| `gui_mouse` | 格内比例坐标定位、鼠标移动、点击、拖动与预览 |
| `gui_keyboard` | 键盘输入与组合键 |
| `gui_batch` | 连续动作按顺序执行，中途失败即停止 |
| `gui_uia` | UIAutomation 控件查询、调用、赋值、选择与展开 |
| `gui_annotate` | 网格框选、箭头、文字标注，以及修改、删除与关闭标注 |

格号从左上开始逐行先右后下；格内坐标原点在左下，x 向右、y 向上。坐标最终映射到物理屏幕像素。递归放大不增加原始细节；新截图不继承旧放大视图。

选择一个窗口或显示器只改变截图范围，输入锁仍覆盖整个桌面。完成最后一个 GUI 动作后立即调用 stop，再处理文件或其他非 GUI 工作；也可按 Esc 退出。标注层独立显示，用户可手动关闭全部标注；GUI 数据保留供后续查看和编辑。软件在线更新不替换用户的工具目录，已有安装通过工具市场单独更新。

## 工具包结构

```text
tools/<tool-id>/
├─ manifest.json
├─ .tool/
│  ├─ tool.json
│  ├─ input.schema.json
│  ├─ output.schema.json
│  ├─ examples.json
│  └─ permissions.json
└─ program/
```

- `manifest.json`：市场身份、版本、作者、许可证和兼容范围。
- `.tool/tool.json`：调用名称、展示名称、用途和运行方式。
- `.tool/input.schema.json`：输入参数合同；顶层参数可用 `permission_type` 声明权限类型。
- `.tool/permissions.json`：该工具各权限点在不同作用范围内的默认处理策略。
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

