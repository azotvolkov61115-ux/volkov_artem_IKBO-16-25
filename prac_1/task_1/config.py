import argparse
from pathlib import Path

from filesystem import DEFAULT_VFS_PATH


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Учебный эмулятор UNIX-оболочки")
    parser.add_argument("--vfs", type=Path, help="путь к JSON-файлу VFS")
    parser.add_argument("--script", type=Path, help="путь к стартовому скрипту")
    return parser.parse_args(arguments)
