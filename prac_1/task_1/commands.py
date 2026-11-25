from collections.abc import Sequence
from typing import TextIO


def execute_command(
    command: str,
    arguments: Sequence[str],
    output: TextIO,
) -> bool:
    if command == "exit":
        return False

    if command in {"ls", "cd"}:
        print(command, *arguments, file=output)
        return True

    print(f"Ошибка: неизвестная команда: {command}", file=output)
    return True
