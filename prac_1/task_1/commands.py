from collections.abc import Sequence
from enum import Enum
from typing import TextIO


class CommandStatus(Enum):
    CONTINUE = "continue"
    EXIT = "exit"
    ERROR = "error"


def execute_command(
    command: str,
    arguments: Sequence[str],
    output: TextIO,
) -> CommandStatus:
    if command == "exit":
        return CommandStatus.EXIT

    if command in {"ls", "cd"}:
        print(command, *arguments, file=output)
        return CommandStatus.CONTINUE

    print(f"Ошибка: неизвестная команда: {command}", file=output)
    return CommandStatus.ERROR
