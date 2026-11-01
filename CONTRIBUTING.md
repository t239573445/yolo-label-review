# Contributing / 参与开发

Use Python 3.10+ in a virtual environment and install from the repository root. / 在虚拟环境中使用 Python 3.10+，从仓库根目录安装：

```bash
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m unittest discover -s tests -v
python -m build
```

GUI tests select Qt's `offscreen` platform automatically. If a graphical desktop is unavailable, the tests still exercise real Qt widgets and input events. Qt runtime libraries may be required by the OS; CI installs the necessary libraries. / GUI 测试自动使用 Qt 的 `offscreen` 模式，无需显示器，仍会检查真实组件和输入事件。系统可能需要安装 Qt 运行库，CI 中已配置。

Use `python -m ruff format .` to format changed files. Keep comments and identifiers in English, and provide English and Simplified Chinese strings for user-visible text. / 使用该命令统一格式；标识符和注释使用英文，面向用户的文字同时提供中英文。

## Layout / 结构

| File | Responsibility / 职责 |
| --- | --- |
| `src/yolo_review/cli.py` | Arguments, lazy GUI startup / 命令行和延迟加载 GUI |
| `gui.py` | Review workflow, selection, history / 审核流程、选择、撤销 |
| `canvas.py` | Image-space rendering and mouse input / 绘图与鼠标交互 |
| `dataset.py` | Validation, backups, atomic label saves / 校验、备份、原子保存 |
| `i18n.py` | UI messages and language resolution / 界面翻译与语言选择 |
| `settings.py` | Atomic position and language preferences / 位置和语言设置 |
| `styles.py` | Desktop theme / 界面样式 |
| `tests/` | Temporary-dataset unit and GUI tests / 临时数据单元与界面测试 |

## Changes / 修改约定

- Never use a real dataset in tests or commit annotations, images, backups, or machine-specific paths. / 测试只用临时数据，不提交真实标签、图片、备份或机器专用路径。
- Keep YOLO parsing strict. A failed save must preserve the previous labels and UI state. / 严格解析 YOLO；保存失败时保留原文件及界面状态。
- Language changes must not reload images, rewrite labels, or discard undo history. Add matching translation keys and placeholders to both catalogs. / 切换语言不能重新加载图片、改写标签或丢弃撤销记录，两份语言表的键和占位符必须一致。
- Preserve held-key navigation and the direct drawing workflow. / 保留长按切图和直接拖框操作。
- Describe the behavior changed and the checks run in pull requests. / 在 PR 中说明行为变更和验证结果。

Build outputs appear in `dist/` and are ignored by Git. A wheel includes only the Python package and metadata; the source distribution also includes documentation and tests. / 构建结果在 `dist/`，Git 会忽略；wheel 包含程序和元数据，源码包还包含文档和测试。
