# YOLO Label Review · YOLO 标注审核

[English](README.md) | 简体中文

**直接拖框，松开即保存。**

用于审核 YOLO 目标检测标注的桌面工具。在图片上按住鼠标左键拖动，就能补充漏标；每次修改自动保存。**画框无需先点击“添加”按钮，修改后无需点击“保存”按钮。**

![直接拖框、松开自动保存，再按 A/D 切换图片](docs/assets/draw-save-zh.gif)

*使用合成示例图片录制的实际界面：直接拖框，松开自动保存，按 D 继续下一张。*

## 三个操作就能开始审核

| 看到的问题 | 直接这样操作 | 结果 |
| --- | --- | --- |
| 漏标了一个目标 | 按住鼠标左键框住目标，松开 | 新框立即保存 |
| 有一个错误标注 | 点击右侧对应条目，按 **Delete / Del** | 选中的框高亮，删除后立即保存 |
| 这张看完了 | 按 **D** 下一张，按 **A** 上一张 | 长按连续切图，松开停止 |

**画框 → 松手 → 继续审核。** 在已有框内部也能直接起笔画新框。多类别数据集先在右侧选择新增框的类别，后续绘制沿用该类别。当前图片改错了可按 **Ctrl+Z** 撤销。

## 功能

- 中文、英文界面，可在使用中切换，无需重新打开数据集。
- 长按 **A / D** 连续切换上一张、下一张，松开停止。
- 点击右侧列表高亮对应框，按 **Delete** 删除。
- 鼠标左键直接拖动新增框，也可从已有框内部起笔。
- 每次修改即时保存，自动备份原标签，支持当前图片的撤销和重做。
- 滚轮缩放、中键平移、序号跳转、记住上次查看位置。
- 保留原始类别名称和 YOLO 归一化格式，无需运行检测模型。

## 安装

需要 **Python 3.10 或更新版本**、PyQt5 和图形桌面。PyQt5 可在 Linux、Windows、macOS 上运行；本地已在 Linux 验证，CI 在 Linux 上检查 Python 3.10 和 3.12。

### 获取代码

仓库目前为私有。让别人使用时，可在仓库的 **Settings → Collaborators** 中邀请对方的 GitHub 账号；对方接受邀请后才能访问和克隆。也可以直接把源码 ZIP 发给对方。共享访问权限不需要将项目公开。

进入 [GitHub 项目页面](https://github.com/t239573445/yolo-label-review)，点击 **Code → Download ZIP** 后解压；或者在已登录 GitHub 的环境中克隆：

```bash
git clone https://github.com/t239573445/yolo-label-review.git
cd yolo-label-review
```

### 首次安装

在解压或克隆后的项目文件夹打开终端。

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

安装命令会一并安装 PyQt5，不需要显卡、模型权重或模型推理服务。项目尚未发布到 PyPI，请按上面的方法在下载的项目目录中安装。

## 启动和语言

将示例路径替换为自己的数据集文件夹，其中应包含 `images/` 和 `labels/`。

**Linux / macOS**（新开终端时需要重新激活同一个环境）：

```bash
source .venv/bin/activate
yolo-review "/你的数据集目录" --lang zh
```

**Windows PowerShell**（在项目文件夹中运行）：

```powershell
.\.venv\Scripts\yolo-review.exe "D:\datasets\我的数据集" --lang zh
```

使用 `--lang en` 可打开英文界面。图片打开后，直接拖动鼠标画框，松开即保存；新增、删除、撤销和重做都自动保存。

在已激活的虚拟环境中，也可使用 `python -m yolo_review "/你的数据集目录"`。不传数据集路径时打开当前工作目录；含空格的路径请加引号。源码目录中，安装 `requirements.txt` 的依赖后，也可直接运行 `python review_annotations.py "/你的数据集目录"`。

顶部 **Language / 语言** 下拉框可即时切换语言，当前图片、框选状态和撤销记录会保留。默认 `--lang auto` 优先使用该数据集上次保存的语言，否则按系统语言选择：中文环境使用简体中文，其他环境使用英文。显式传入 `--lang zh` 或 `--lang en` 会覆盖已保存的选择。数据集自己的类别名称不会翻译。

运行 `yolo-review --lang zh --help` 查看中文帮助，`yolo-review --help` 查看默认语言帮助，`yolo-review --version` 查看版本。这些命令无需打开窗口。

## 数据集结构

```text
数据集目录/
├── images/
│   ├── frame001.png
│   └── train/frame002.jpg
├── labels/
│   ├── frame001.txt
│   └── train/frame002.txt
└── classes.txt
```

递归读取 `images/` 下的图片并按文件名自然排序。标签对应图片在 `images/` 下的相对路径，在 `labels/` 下使用同名 `.txt` 文件。支持 PNG、JPG/JPEG、BMP、WebP、TIF/TIFF，实际解码能力取决于已安装的 Qt 图片插件。`classes.txt` 使用 UTF-8，每行一个类别名称，从类别 0 开始；缺省名称显示类别编号。程序直接读取这些目录，不使用 `data.yaml` 中的数据集路径或训练/验证划分。

每行标签必须恰好包含五列：

```text
class_id x_center y_center width height
0 0.500000 0.500000 0.200000 0.100000
```

坐标归一化到 0～1，宽高必须大于零。仅支持普通矩形检测框，不支持分割、关键点或旋转框。缺失的标签视为空，在首次修改时创建。删除最后一个框后保留空标签文件。遇到格式错误会禁止编辑当前图片并显示原因，避免丢失原标注。

## 操作

| 操作 | 方法 |
| --- | --- |
| 上一张 / 下一张 | A / D；长按连续切图，速度跟随系统键盘重复设置 |
| 选择并高亮框 | 点击右侧列表条目 |
| 删除选中框 | Delete / Del |
| 添加框 | 直接按住鼠标左键拖动，松开即保存 |
| 修改框的位置或大小 | 删除后重新绘制 |
| 撤销 / 重做 | Ctrl+Z / Ctrl+Shift+Z 或 Ctrl+Y |
| 缩放 / 平移 | 滚轮 / 按住鼠标中键拖动 |
| 适应窗口 | F |
| 取消绘制 / 选择 | Esc |
| 跳转 | 输入从 1 开始的图片序号，按回车或点击“前往” |

切换图片后会清空撤销记录。拖框的宽、高均须达到原图的两个像素才会新增。绿色是已有框，黄色是当前选中框，蓝色是正在绘制的框。

## 保存和恢复

新增、删除、撤销、重做都会先写临时文件，再原子替换标签，成功后才更新界面。同一数据集仅允许一个审核窗口编辑。程序通过版本校验检测其他软件修改标签的情况；发生冲突时，切换图片重新加载后再编辑。本工具用于本地审核，不是多人协作标注服务器。

每个标签首次修改前会备份至 `.yolo_review/backups/labels/` 对应路径，后续修改不会覆盖原始备份。恢复时先关闭程序，再将备份复制回 `labels/` 对应位置。若备份为 `.txt.missing` 标记，说明原本没有标签，恢复原状时删除新建的标签文件即可。

`.yolo_review/state.json` 保存图片位置和语言。仅查看图片、选框、切换语言不会改写标签。备份保存在数据集本地，需要迁移时请随数据集一起复制。

## 开发

开发环境、测试、代码格式、架构和构建命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。GitHub Actions 在推送和 Pull Request 时自动检查。所有自动测试都使用临时生成的数据。

`.gitignore` 排除了图片、标签、模型、审核备份、虚拟环境和构建缓存。分享软件时，项目源码和数据集分别管理。

## 许可证

项目源码采用 [MIT License](LICENSE)。依赖沿用各自许可证；PyQt5 使用 GPL v3 或商业许可证，本项目的 MIT 许可不替代 PyQt5 的许可条款。
