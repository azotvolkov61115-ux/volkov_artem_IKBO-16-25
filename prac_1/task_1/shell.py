import sys
from typing import TextIO

from command_parser import CommandParseError, parse_command
from commands import CommandStatus, execute_command


def run_shell(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    vfs_name: str = "my_vfs",
) -> None:
    if input_stream is None:
        input_stream = sys.stdin
    if output_stream is None:
        output_stream = sys.stdout

    current_directory = "/"

    while True:
        print(f"{vfs_name}:{current_directory}$ ", end="", flush=True, file=output_stream)
        line = input_stream.readline()
        if line == "":
            return

        status = execute_line(line, output_stream)
        if status is CommandStatus.EXIT:
            return


def run_script(
    script_path: str,
    vfs_name: str,
    output_stream: TextIO,
) -> CommandStatus:
    current_directory = "/"

    try:
        script = open(script_path, encoding="utf-8")
    except OSError as error:
        print(f"Ошибка: не удалось открыть стартовый скрипт: {error}", file=output_stream)
        return CommandStatus.ERROR

    try:
        with script:
            for line in script:
                command_line = line.rstrip("\r\n")
                if not command_line.strip():
                    continue

                print(f"{vfs_name}:{current_directory}$ {command_line}", file=output_stream)
                status = execute_line(command_line, output_stream)
                if status is not CommandStatus.CONTINUE:
                    return status
    except (OSError, UnicodeError) as error:
        print(f"Ошибка: не удалось прочитать стартовый скрипт: {error}", file=output_stream)
        return CommandStatus.ERROR

    return CommandStatus.CONTINUE


def execute_line(line: str, output_stream: TextIO) -> CommandStatus:
    try:
        parts = parse_command(line)
    except CommandParseError as error:
        print(f"Ошибка: {error}", file=output_stream)
        return CommandStatus.ERROR

    if not parts:
        return CommandStatus.CONTINUE

    return execute_command(parts[0], parts[1:], output_stream)
