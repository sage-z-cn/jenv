# jenv

[中文](README-zh.md)

Windows JDK version manager. Scans for JDK installations and switches the `JAVA_HOME` environment variable with a single command.

## Install

Download `dist/jenv.exe` and place it anywhere in your `PATH`.

## Usage

```
jenv list                 List all installed JDKs
jenv current              Show current JAVA_HOME
jenv use  <version>       Switch JDK version (requires admin)
jenv dirs [list]          List scan directories
jenv dirs add    <dir>    Add a scan directory
jenv dirs remove <dir>    Remove a scan directory
jenv dirs reset           Reset to defaults
jenv help                 Show help
```

## Example

```
> jenv list
    1.8  C:\Program Files\Java\jdk1.8.0_202
>>   17  C:\Program Files\Eclipse Adoptium\jdk-17.0.10.7-hotspot
     25  C:\Program Files\Eclipse Adoptium\jdk-25.0.1.8-hotspot

> jenv use 25
JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-25.0.1.8-hotspot
Restart your terminal / IDE for the changes to take effect.
```

`>>` marks the currently active version. Restart your terminal or IDE after switching for changes to take effect.

## Default scan directories

- `C:\Program Files\Eclipse Adoptium`
- `C:\Program Files\Java`

Add custom directories with `jenv dirs add <dir>`. Config is stored at `%USERPROFILE%\.config\jenv\config.json`.

## Build

Requires Python 3 and PyInstaller:

```
pip install pyinstaller
python -m PyInstaller jenv.spec
```

Or use the VS Code task `jenv: build`.

## Version detection

- `jdk-17.0.10` → version `17`
- `jdk1.8.0_202` → version `1.8`
- `jdk-25.0.1`  → version `25`
