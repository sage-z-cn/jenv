import argparse
import ctypes
import json
import os
import sys
import winreg
from collections import OrderedDict
from pathlib import Path

RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
RESET = "\033[0m"


def _enable_virtual_terminal() -> None:
    """Enable ANSI escape sequence processing on Windows console."""
    if sys.platform != "win32":
        return
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    mode = ctypes.c_uint32()
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

DEFAULT_SEARCH_DIRS = [
    r"C:\Program Files\Eclipse Adoptium",
    r"C:\Program Files\Java",
]

CONFIG_DIR = Path.home() / ".config" / "jenv"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load_config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _get_search_dirs() -> list[str]:
    config = _load_config()
    return config.get("search_dirs", DEFAULT_SEARCH_DIRS)

REG_HIVE = winreg.HKEY_LOCAL_MACHINE
REG_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"


def extract_version(dirname: str) -> str | None:
    """Extract short version from directory name like jdk-17, jdk1.8.0_202."""
    name = dirname.lower().strip()
    if name.startswith("jdk-"):
        rest = name[4:]
    elif name.startswith("jdk"):
        rest = name[3:]
    else:
        return None

    if not rest:
        return None

    if rest.startswith("1."):
        parts = rest.split(".")
        if len(parts) >= 2:
            return f"1.{parts[1]}"
    else:
        parts = rest.split(".")
        if parts[0].isdigit():
            return parts[0]

    return None


def find_jdks() -> OrderedDict[str, Path]:
    jdks = OrderedDict()
    for search_dir in _get_search_dirs():
        p = Path(search_dir)
        if not p.is_dir():
            continue
        for entry in sorted(p.iterdir()):
            if not entry.is_dir():
                continue
            version = extract_version(entry.name)
            if version:
                jdks[version] = entry
    return jdks


def get_current_java_home() -> str | None:
    try:
        with winreg.OpenKey(REG_HIVE, REG_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "JAVA_HOME")
            return value
    except (FileNotFoundError, OSError):
        return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def broadcast_change() -> None:
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
        SMTO_ABORTIFHUNG, 5000, None,
    )


def cmd_list() -> None:
    jdks = find_jdks()
    if not jdks:
        print("No JDK installations found.")
        return
    current_path = get_current_java_home()
    if current_path:
        current_path = current_path.rstrip("\\/")
    for version, path in jdks.items():
        is_current = current_path and Path(current_path) == path
        marker = ">>" if is_current else "  "
        line = f"{marker} {version:>6}  {path}"
        if is_current:
            line = f"{GREEN}{line}{RESET}"
        print(line)


def cmd_current() -> None:
    current = get_current_java_home()
    if not current:
        print(f"{CYAN}JAVA_HOME is not set.{RESET}")
        return
    jdks = find_jdks()
    version = None
    current_path = Path(current.rstrip("\\/"))
    for ver, path in jdks.items():
        if path == current_path:
            version = ver
            break
    print(f"{GREEN}JAVA_HOME = {current}{RESET}")
    if version:
        print(f"{CYAN}Version:    {version}{RESET}")
    else:
        print(f"{RED}(not found in known installations){RESET}")


def _read_reg_string(key_handle, name: str) -> str:
    try:
        value, _ = winreg.QueryValueEx(key_handle, name)
        return value
    except (FileNotFoundError, OSError):
        return ""


def _write_reg_string(key_handle, name: str, value: str) -> None:
    winreg.SetValueEx(key_handle, name, 0, winreg.REG_EXPAND_SZ, value)


JAVA_BIN_ENTRY = r"%JAVA_HOME%\bin"


def _ensure_path_has_java_bin() -> bool:
    """Return True if PATH already contained the entry (no change needed)."""
    with winreg.OpenKey(REG_HIVE, REG_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
        current_path = _read_reg_string(key, "Path")

        entries = [p.strip() for p in current_path.split(";") if p.strip()]
        if any(e.upper() == JAVA_BIN_ENTRY.upper() for e in entries):
            return True

        entries.append(JAVA_BIN_ENTRY)
        _write_reg_string(key, "Path", ";".join(entries))

    broadcast_change()
    return False


def cmd_use(version: str) -> None:
    jdks = find_jdks()
    if version not in jdks:
        print(f"{RED}Unknown version: {version}{RESET}")
        print(f"Available: {', '.join(jdks.keys())}")
        sys.exit(1)

    if not is_admin():
        print(f"{RED}ERROR: Administrator privileges required.{RESET}")
        print("Please run as Administrator.")
        sys.exit(2)

    target_path = str(jdks[version])
    try:
        with winreg.OpenKey(REG_HIVE, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            _write_reg_string(key, "JAVA_HOME", target_path)
    except OSError as e:
        print(f"{RED}Failed to set JAVA_HOME: {e}{RESET}")
        sys.exit(3)

    broadcast_change()

    already_in_path = _ensure_path_has_java_bin()

    print(f"{GREEN}JAVA_HOME = {target_path}{RESET}")
    if not already_in_path:
        print(f"{GREEN}Added %JAVA_HOME%\\bin to system Path{RESET}")
    print("Restart your terminal / IDE for the changes to take effect.")


def cmd_dirs_list() -> None:
    dirs = _get_search_dirs()
    if not dirs:
        print(f"{CYAN}No scan directories configured.{RESET}")
        return
    for d in dirs:
        exists = Path(d).is_dir()
        status = f"{GREEN}(exists){RESET}" if exists else f"{RED}(not found){RESET}"
        print(f"  {d}  {status}")


def cmd_dirs_add(directory: str) -> None:
    target = str(Path(directory).resolve())
    config = _load_config()
    dirs: list[str] = config.get("search_dirs", DEFAULT_SEARCH_DIRS.copy())
    if target in dirs:
        print(f"{CYAN}Already in search dirs: {target}{RESET}")
        return
    dirs.append(target)
    config["search_dirs"] = dirs
    _save_config(config)
    print(f"{GREEN}Added: {target}{RESET}")


def cmd_dirs_remove(directory: str) -> None:
    target = str(Path(directory).resolve())
    config = _load_config()
    dirs: list[str] = config.get("search_dirs", DEFAULT_SEARCH_DIRS.copy())
    if target not in dirs:
        print(f"{CYAN}Not in search dirs: {target}{RESET}")
        return
    dirs.remove(target)
    config["search_dirs"] = dirs
    _save_config(config)
    print(f"{GREEN}Removed: {target}{RESET}")


def cmd_dirs_reset() -> None:
    config = _load_config()
    if "search_dirs" not in config:
        print(f"{CYAN}Already using defaults.{RESET}")
        return
    del config["search_dirs"]
    if config:
        _save_config(config)
    else:
        try:
            os.remove(CONFIG_FILE)
        except OSError:
            pass
    print(f"{GREEN}Reset to default search directories.{RESET}")


def cmd_help() -> None:
    print(f"{CYAN}jenv - Java environment manager{RESET}\n"
          "\n"
          "Commands:\n"
          "  list      List all installed JDKs\n"
          "  current   Show current JAVA_HOME\n"
          "  use  <version>  Switch JDK version (requires admin)\n"
          "  dirs      Manage JDK scan directories\n"
          "  help      Show this help message\n"
          "\n"
          "Dirs subcommands:\n"
          "  dirs [list]          List scan directories\n"
          "  dirs add    <dir>    Add a scan directory\n"
          "  dirs remove <dir>    Remove a scan directory\n"
          "  dirs reset           Reset to defaults\n"
          "\n"
          "Examples:\n"
          "  jenv list              # List available JDKs\n"
          "  jenv current           # Show current JDK\n"
          "  jenv use 17            # Switch to JDK 17\n"
          "  jenv use 1.8           # Switch to JDK 1.8\n"
          "  jenv dirs add D:\\jdks   # Add custom JDK directory\n"
          "\n"
          "Supported installation directories:\n" +
          "\n".join(f"  {d}" for d in _get_search_dirs()))


def main() -> None:
    _enable_virtual_terminal()

    parser = argparse.ArgumentParser(
        description="jenv - Java environment manager", add_help=False
    )

    err_msg = []

    def _error(self, message):
        err_msg.append(message)
        raise SystemExit

    parser.error = _error.__get__(parser)
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List all installed JDKs", add_help=False)
    p_current = sub.add_parser("current", help="Show current JAVA_HOME", add_help=False)
    p_use = sub.add_parser("use", help="Switch to a specific JDK version", add_help=False)
    p_dirs = sub.add_parser("dirs", help="Manage JDK scan directories", add_help=False)
    p_help = sub.add_parser("help", help="Show help information", add_help=False)

    for p in (p_list, p_current, p_use, p_dirs, p_help):
        p.error = _error.__get__(p)

    dirs_sub = p_dirs.add_subparsers(dest="dirs_action")
    dirs_sub.add_parser("add", help="Add a scan directory", add_help=False).add_argument("directory", help="Directory path")
    dirs_sub.add_parser("remove", help="Remove a scan directory", add_help=False).add_argument("directory", help="Directory path")
    dirs_sub.add_parser("list", help="List scan directories", add_help=False)
    dirs_sub.add_parser("reset", help="Reset to defaults", add_help=False)

    p_use.add_argument(
        "version", help="Version to switch to (e.g. 17, 1.8, 25)"
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        cmd_help()
        if err_msg:
            print(f"\n{RED}error: {err_msg[0]}{RESET}")
        sys.exit(0)

    if args.command == "list":
        cmd_list()
    elif args.command == "current":
        cmd_current()
    elif args.command == "use":
        cmd_use(args.version)
    elif args.command == "dirs":
        if args.dirs_action == "add":
            cmd_dirs_add(args.directory)
        elif args.dirs_action == "remove":
            cmd_dirs_remove(args.directory)
        elif args.dirs_action == "reset":
            cmd_dirs_reset()
        else:
            cmd_dirs_list()
    elif args.command == "help":
        cmd_help()
    else:
        cmd_help()


if __name__ == "__main__":
    main()
