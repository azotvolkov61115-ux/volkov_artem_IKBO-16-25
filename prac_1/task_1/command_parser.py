import shlex


class CommandParseError(ValueError):
    pass


def parse_command(line: str) -> list[str]:
    try:
        return shlex.split(line)
    except ValueError as error:
        raise CommandParseError("незакрытая кавычка") from error
