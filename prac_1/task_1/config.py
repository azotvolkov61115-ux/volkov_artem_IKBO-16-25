import argparse
from pathlib import Path


DEFAULT_VFS_PATH = Path(__file__).with_name("vfs.json")


def parse_arguments(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Учебный эмулятор UNIX-оболочки")
    parser.add_argument("--vfs", type=Path, help="путь к JSON-файлу VFS")
    parser.add_argument("--script", type=Path, help="путь к стартовому скрипту")
    return parser.parse_args(arguments)
