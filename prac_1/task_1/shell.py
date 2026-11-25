import sys
from typing import TextIO

from command_parser import CommandParseError, parse_command
from commands import execute_command


def run_shell(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    if input_stream is None:
        input_stream = sys.stdin
    if output_stream is None:
        output_stream = sys.stdout

    vfs_name = "my_vfs"
    current_directory = "/"

    while True:
        print(f"{vfs_name}:{current_directory}$ ", end="", flush=True, file=output_stream)
        line = input_stream.readline()
        if line == "":
            return

        try:
            parts = parse_command(line)
        except CommandParseError as error:
            print(f"Ошибка: {error}", file=output_stream)
            continue

        if not parts:
            continue

        if not execute_command(parts[0], parts[1:], output_stream):
            return
