import io
import unittest

from command_parser import CommandParseError, parse_command
from shell import run_shell


class CommandParserTests(unittest.TestCase):
    def test_parses_command_and_quoted_arguments(self) -> None:
        self.assertEqual(
            parse_command('cp "my file.txt" \'new file.txt\''),
            ["cp", "my file.txt", "new file.txt"],
        )

    def test_empty_line_has_no_arguments(self) -> None:
        self.assertEqual(parse_command("   "), [])

    def test_unclosed_quote_is_reported(self) -> None:
        with self.assertRaisesRegex(CommandParseError, "незакрытая кавычка"):
            parse_command('ls "unfinished')


class ShellTests(unittest.TestCase):
    def test_shell_commands_and_errors(self) -> None:
        input_stream = io.StringIO('ls "my folder"\nunknown\nls "unfinished\n\nexit\n')
        output_stream = io.StringIO()

        run_shell(input_stream, output_stream)

        output = output_stream.getvalue()
        self.assertIn("my_vfs:/$ ", output)
        self.assertIn("ls my folder", output)
        self.assertIn("Ошибка: неизвестная команда: unknown", output)
        self.assertIn("Ошибка: незакрытая кавычка", output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
