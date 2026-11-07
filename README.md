# 喜马拉雅 XM 解密工具

此工具用于解密喜马拉雅下载下来的 `.xm` 文件成普通音频。会尽量保留完整信息，输出支持 `m4a`、`mp3`、`flac` 和 `wav`等格式

当前版本：**v1.0.7**

> 请遵守喜马拉雅的服务条款、版权规定和当地法律。本程序仅供学习使用，下载后请于3天内删除。

## 功能

- 单个文件解密：从文件选择窗口选一个 `.xm` 文件。
- 批量解密：选择文件夹后处理其中第一层的 `.xm` 文件，不会递归扫描子目录。
- 自动识别格式：解密后保存为 `m4a`、`mp3`、`flac` 或 `wav`。
- 保留基本信息：不会更改标题，作者等信息
- 完整性检查：空文件、元数据缺失、文件损坏或音频格式无法识别时，会记录到失败清单，不会让整个批处理直接中断。
- 文件名保护：清理 Windows 不允许使用的字符和保留设备名；遇到同名文件会自动加 `(1)`、`(2)`，不会静默覆盖。
- 附带 `rename.py`：按文件名中的集数统一补零排序。

## 获取程序

在 [Releases](https://github.com/a176073240-cmd/Ximalaya-Decrypt-Enhance/releases) 下载最新版本。

如果你只想直接用，下载 `Ximalaya-Decrypt-v1.0.7-Windows-x64.zip`，解压后按需要运行：

```text
Ximalaya-Decrypt.exe   # 解密 XM 文件
Ximalaya-Rename.exe    # 整理音频文件名
README.md
```

对小白说的话：双击 EXE 就能在win系统上运行，不需要另外安装 Python，也不需要单独准备 `xm_encryptor.wasm`。

如果你更想看源码或自己构建，Release 页面也可以直接下载源码，下面是源码运行方法。

## 源码运行

建议使用 64 位 Windows 和 Python 3.10 或更高版本。进入项目目录后，在 PowerShell 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install mutagen pycryptodome wasmtime python-magic-bin
python main.py
```

如果 PowerShell 拦截了虚拟环境脚本，可以直接调用虚拟环境里的 Python：

```powershell
.\.venv\Scripts\python.exe main.py
```

源码运行时，`xm_encryptor.wasm` 必须和 `main.py` 放在同一目录。

## 解密流程

1. 运行 `main.py`，或者双击 `Ximalaya-Decrypt.exe`。
2. 选择“解密单个文件”或“批量解密文件”。
3. 选择是否使用 XM 文件内的集数生成前缀，例如 `0204 - 标题.m4a`。
4. 选择输出目录；不指定时，文件会放到程序目录下的 `output` 文件夹。
5. 等待任务完成。失败文件会列出文件名和原因，其他文件会继续处理。

输出目录大致如下：

```text
output/
└─ 专辑名称/
   ├─ 0204 - 第204集.m4a
   └─ 第205集.m4a
```

批量模式只读取所选目录的第一层。如果音频分散在多个子目录里，请分别选择这些目录。

## 文件名排序工具

`rename.py` 或 `Ximalaya-Rename.exe` 都可以用来整理已经解密好的音频文件名，支持 `.mp3`、`.m4a`、`.flac` 和 `.wav`。

选择音频文件夹后，工具会尝试：

- 去掉已有的 `[0001]` 这类旧前缀；
- 找到文件名中的第一段数字，把它当作集数；
- 生成类似 `[0001] 标题.m4a` 的新名称；
- 检查目标名称是否重复，冲突文件会进入失败清单。

它只处理当前文件夹，不会递归子目录。标题本身带数字时，改名后请检查一下结果；批量操作前也建议先备份。

## v1.0.7 更新

- 修复非 XM 文件、损坏 ID3 元数据、截断加密数据和无效 AES 初始向量的错误识别。
- 增加输入校验回归测试，避免底层库异常直接中断批量任务。
- 保留 v1.0.6 的 Windows 64 位 EXE 和 Wasmtime 打包方式。

## 常见问题

### 双击 EXE 没有反应

这是命令行程序，双击后会打开一个控制台窗口。窗口一闪而过时，请在 PowerShell 中运行 EXE，这样能看到具体报错。Windows Defender 如果弹出提示，请确认文件来自本项目的 Release 页面。

### `ModuleNotFoundError`

这是源码运行时的依赖问题。确认当前终端使用的是你安装依赖的 Python，然后重新执行：

```powershell
python -m pip install mutagen pycryptodome wasmtime python-magic-bin
```

### 找不到 `xm_encryptor.wasm`

只有源码运行才需要这个文件。确认它和 `main.py` 在同一目录；Release 里的 EXE 已经把它打包进去了。

### `unexpected format`

通常是 `.xm` 文件没有下载完整、文件已经损坏，或者当前格式暂不支持。重新下载源文件后再试。

### 文件选择窗口没有弹出

工具需要 Windows 桌面环境。请不要在没有图形界面的服务器或远程终端里启动。

## 鸣谢

这个项目是在 [sld272/Ximalaya-XM-Decrypt](https://github.com/sld272/Ximalaya-XM-Decrypt) 的基础上继续维护和改进的。

解密原理参考 [Aynakeya：喜马拉雅 XM 文件解密逆向分析](https://www.aynakeya.com/2023/03/15/ctf/xi-ma-la-ya-xm-wen-jian-jie-mi-ni-xiang-fen-xi/)。感谢相关作者和研究者的技术分享。

遇到问题时，欢迎附上错误信息、文件大小和音频格式。请不要上传带有个人信息或版权受限的音频文件。

## 免责声明与来源说明

本项目仅用于处理用户已经合法取得、并且有权使用的本地 `.xm` 文件。
本工具不提供账号登录、付费内容获取或绕过平台授权的功能。

请遵守喜马拉雅服务条款、版权规定和当地法律。因使用本项目产生的任何后果，由使用者自行承担。

本项目包含来源于第三方项目和技术研究的代码、算法实现及 `xm_encryptor.wasm`。相关内容的权利归其合法权利人所有，本项目不声明对这些第三方内容拥有所有权，也不授予超出原权利范围的再授权。

## 许可证

本项目当前未声明统一的开源许可证。

仓库包含来源于第三方项目及技术研究的内容，无法确认所有相关代码、算法和文件都具备统一再授权条件。使用、修改或再分发前，请自行确认相关内容的授权情况。
