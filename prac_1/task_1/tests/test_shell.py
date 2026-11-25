import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from command_parser import CommandParseError, parse_command
from commands import CommandStatus
from main import main
from shell import run_script, run_shell


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

    def test_script_echoes_commands_and_stops_on_first_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "commands.txt"
            script_path.write_text('\nls "a folder"\nunknown\nexit\n', encoding="utf-8")
            output_stream = io.StringIO()

            status = run_script(str(script_path), "demo", output_stream)

        self.assertIs(status, CommandStatus.ERROR)
        output = output_stream.getvalue()
        self.assertIn('demo:/$ ls "a folder"', output)
        self.assertIn("ls a folder", output)
        self.assertIn("Ошибка: неизвестная команда: unknown", output)
        self.assertNotIn("demo:/$ exit", output)

    def test_script_exit_stops_without_reading_later_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "commands.txt"
            script_path.write_text("exit\nunknown\n", encoding="utf-8")
            output_stream = io.StringIO()

            status = run_script(str(script_path), "demo", output_stream)

        self.assertIs(status, CommandStatus.EXIT)
        self.assertNotIn("unknown", output_stream.getvalue())


class StartupTests(unittest.TestCase):
    def test_cli_runs_script_then_enters_interactive_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vfs_path = Path(directory) / "sample.json"
            script_path = Path(directory) / "commands.txt"
            vfs_path.write_text("{}", encoding="utf-8")
            script_path.write_text("ls\n", encoding="utf-8")
            output_stream = io.StringIO()

            with patch("sys.stdout", output_stream), patch("sys.stdin", io.StringIO("")):
                status = main(["--vfs", str(vfs_path), "--script", str(script_path)])

        self.assertEqual(status, 0)
        output = output_stream.getvalue()
        self.assertIn(f"VFS: {vfs_path}", output)
        self.assertIn(f"Стартовый скрипт: {script_path}", output)
        self.assertIn("sample:/$ ls", output)
        self.assertIn("sample:/$ ", output)

    def test_missing_vfs_returns_error_without_starting_shell(self) -> None:
        output_stream = io.StringIO()
        error_stream = io.StringIO()
        with patch("sys.stdout", output_stream), patch("sys.stderr", error_stream):
            status = main(["--vfs", "/path/that/does/not/exist.json"])

        self.assertEqual(status, 1)
        self.assertIn("файл VFS не найден", error_stream.getvalue())
        self.assertNotIn("my_vfs:/$", output_stream.getvalue())

    def test_missing_script_returns_error_without_starting_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vfs_path = Path(directory) / "sample.json"
            vfs_path.write_text("{}", encoding="utf-8")
            output_stream = io.StringIO()
            error_stream = io.StringIO()

            with patch("sys.stdout", output_stream), patch("sys.stderr", error_stream):
                status = main(["--vfs", str(vfs_path), "--script", str(Path(directory) / "missing.txt")])

        self.assertEqual(status, 1)
        self.assertIn("стартовый скрипт не найден", error_stream.getvalue())
        self.assertNotIn("sample:/$", output_stream.getvalue())

    def test_failed_startup_script_does_not_enter_interactive_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vfs_path = Path(directory) / "sample.json"
            script_path = Path(directory) / "commands.txt"
            vfs_path.write_text("{}", encoding="utf-8")
            script_path.write_text("unknown\n", encoding="utf-8")
            output_stream = io.StringIO()
            error_stream = io.StringIO()

            with patch("sys.stdout", output_stream), patch("sys.stderr", error_stream):
                status = main(["--vfs", str(vfs_path), "--script", str(script_path)])

        self.assertEqual(status, 1)
        self.assertIn("Ошибка: неизвестная команда: unknown", output_stream.getvalue())
        self.assertEqual(output_stream.getvalue().count("sample:/$ "), 1)


if __name__ == "__main__":
    unittest.main()
