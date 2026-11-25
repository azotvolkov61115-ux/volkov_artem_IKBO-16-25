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

    if command in {"ls", "cd"}:
        print(command, *arguments, file=output)
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
