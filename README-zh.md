# jenv

[English](README.md)

Windows JDK 版本管理工具。扫描系统中的 JDK 安装，一键切换 `JAVA_HOME` 环境变量。

## 安装

下载 `dist/jenv.exe`，放到任意位于 `PATH` 的目录即可。

## 用法

```
jenv list                 列出所有已安装的 JDK
jenv current              显示当前 JAVA_HOME
jenv use  <版本>           切换 JDK 版本（需管理员权限）
jenv dirs [list]          列出扫描目录
jenv dirs add    <目录>    添加扫描目录
jenv dirs remove <目录>    移除扫描目录
jenv dirs reset           重置为默认目录
jenv help                 显示帮助
```

## 示例

```
> jenv list
    1.8  C:\Program Files\Java\jdk1.8.0_202
>>   17  C:\Program Files\Eclipse Adoptium\jdk-17.0.10.7-hotspot
     25  C:\Program Files\Eclipse Adoptium\jdk-25.0.1.8-hotspot

> jenv use 25
JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-25.0.1.8-hotspot
Restart your terminal / IDE for the changes to take effect.
```

`>>` 标记当前使用的版本，切换后需重启终端或 IDE 使环境变量生效。

## 默认扫描目录

- `C:\Program Files\Eclipse Adoptium`
- `C:\Program Files\Java`

通过 `jenv dirs add <目录>` 添加自定义目录。配置保存在 `%USERPROFILE%\.config\jenv\config.json`。

## 构建

需要 Python 3 和 PyInstaller：

```
pip install pyinstaller
python -m PyInstaller jenv.spec
```

或使用 VS Code 任务 `jenv: build`。

## 版本识别

- `jdk-17.0.10` → 版本 `17`
- `jdk1.8.0_202` → 版本 `1.8`
- `jdk-25.0.1`  → 版本 `25`
