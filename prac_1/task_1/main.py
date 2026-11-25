import sys
from pathlib import Path
from typing import Sequence

from commands import CommandStatus
from config import DEFAULT_VFS_PATH, parse_arguments
from filesystem import FileSystemError, VirtualFileSystem
from shell import run_script, run_shell


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(list(arguments) if arguments is not None else None)
    vfs_path = options.vfs or DEFAULT_VFS_PATH

    print(f"VFS: {vfs_path}" if options.vfs else f"VFS по умолчанию: {vfs_path}")
    print(f"Стартовый скрипт: {options.script}" if options.script else "Стартовый скрипт: не задан")

    if not vfs_path.is_file():
        print(f"Ошибка: файл VFS не найден: {vfs_path}", file=sys.stderr)
        return 1

    if options.script is not None and not options.script.is_file():
        print(f"Ошибка: стартовый скрипт не найден: {options.script}", file=sys.stderr)
        return 1

    try:
        filesystem = VirtualFileSystem.load(vfs_path)
    except FileSystemError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    vfs_name = Path(vfs_path).stem
    if options.script is not None:
        script_status = run_script(
            str(options.script),
            vfs_name,
            sys.stdout,
            filesystem,
        )
        if script_status is CommandStatus.ERROR:
            return 1
        if script_status is CommandStatus.EXIT:
            return 0

    run_shell(vfs_name=vfs_name, filesystem=filesystem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
