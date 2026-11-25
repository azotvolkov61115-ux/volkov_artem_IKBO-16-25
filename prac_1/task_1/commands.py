import sys
from collections.abc import Sequence
from enum import Enum
from typing import TextIO

from filesystem import FileSystemError, VirtualFileSystem


class CommandStatus(Enum):
    CONTINUE = "continue"
    EXIT = "exit"
    ERROR = "error"


def execute_command(
    command: str,
    arguments: Sequence[str],
    output: TextIO,
    filesystem: VirtualFileSystem | None = None,
) -> CommandStatus:
    if command == "exit":
        return CommandStatus.EXIT

    if filesystem is None and command in {"ls", "cd", "pwd", "uniq", "cp", "chown"}:
        print("Ошибка: VFS не загружена", file=output)
        return CommandStatus.ERROR

    if command == "ls":
        if len(arguments) > 1:
            print("Ошибка: использование: ls [ПУТЬ]", file=output)
            return CommandStatus.ERROR
        path = arguments[0] if arguments else filesystem.current_directory
        try:
            node = filesystem.resolve(path)
            if node["type"] != "directory":
                print(f"Ошибка: это не директория: {path}", file=output)
                return CommandStatus.ERROR
        except FileSystemError as error:
            print(f"Ошибка: {error}", file=output)
            return CommandStatus.ERROR
        for name in node["children"]:
            print(name, file=output)
        return CommandStatus.CONTINUE

    if command == "cd":
        if len(arguments) > 1:
            print("Ошибка: использование: cd [ПУТЬ]", file=output)
            return CommandStatus.ERROR
        try:
            filesystem.change_directory(arguments[0] if arguments else "/")
        except FileSystemError as error:
            print(f"Ошибка: {error}", file=output)
            return CommandStatus.ERROR
        return CommandStatus.CONTINUE

    if command == "pwd":
        if arguments:
            print("Ошибка: использование: pwd", file=output)
            return CommandStatus.ERROR
        print(filesystem.current_directory, file=output)
        return CommandStatus.CONTINUE

    if command == "clear":
        if arguments:
            print("Ошибка: использование: clear", file=output)
            return CommandStatus.ERROR
        if output.isatty():
            try:
                output.write("\033[2J\033[H")
                output.flush()
            except OSError as error:
                print(f"Предупреждение: не удалось очистить экран: {error}", file=sys.stderr)
        return CommandStatus.CONTINUE

    if command == "uniq":
        if len(arguments) != 1:
            print("Ошибка: использование: uniq ПУТЬ_К_ФАЙЛУ", file=output)
            return CommandStatus.ERROR
        try:
            node = filesystem.resolve(arguments[0])
            if node["type"] != "file":
                print(f"Ошибка: это не файл: {arguments[0]}", file=output)
                return CommandStatus.ERROR
        except FileSystemError as error:
            print(f"Ошибка: {error}", file=output)
            return CommandStatus.ERROR

        previous_line = None
        for line in node["content"].splitlines(keepends=True):
            comparison_line = line.removesuffix("\n").removesuffix("\r")
            if comparison_line != previous_line:
                output.write(line)
            previous_line = comparison_line
        return CommandStatus.CONTINUE

    if command == "cp":
        if len(arguments) != 2:
            print("Ошибка: использование: cp ИСХОДНЫЙ_ФАЙЛ НАЗНАЧЕНИЕ", file=output)
            return CommandStatus.ERROR
        try:
            copied_path = filesystem.copy_file(arguments[0], arguments[1])
        except FileSystemError as error:
            print(f"Ошибка: {error}", file=output)
            return CommandStatus.ERROR
        print(f"Файл скопирован: {copied_path}", file=output)
        return CommandStatus.CONTINUE

    if command == "chown":
        if len(arguments) != 2:
            print("Ошибка: использование: chown ВЛАДЕЛЕЦ ПУТЬ", file=output)
            return CommandStatus.ERROR
        try:
            filesystem.change_owner(arguments[0], arguments[1])
        except FileSystemError as error:
            print(f"Ошибка: {error}", file=output)
            return CommandStatus.ERROR
        print(f"Владелец объекта изменен: {arguments[1]}", file=output)
        return CommandStatus.CONTINUE

    if command in {"vfs-save", "vfs-init"}:
        if filesystem is None:
            print("Ошибка: VFS не загружена", file=output)
            return CommandStatus.ERROR

        if command == "vfs-save":
            if len(arguments) != 1:
                print("Ошибка: использование: vfs-save ПУТЬ", file=output)
                return CommandStatus.ERROR
            try:
                filesystem.save(arguments[0])
            except FileSystemError as error:
                print(f"Ошибка: {error}", file=output)
                return CommandStatus.ERROR
            print(f"VFS сохранена: {arguments[0]}", file=output)
            return CommandStatus.CONTINUE

        if arguments:
            print("Ошибка: команда vfs-init не принимает аргументы", file=output)
            return CommandStatus.ERROR
        filesystem.reset()
        print("VFS сброшена к состоянию по умолчанию", file=output)
        return CommandStatus.CONTINUE

    print(f"Ошибка: неизвестная команда: {command}", file=output)
    return CommandStatus.ERROR
