import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from command_parser import CommandParseError, parse_command
from commands import CommandStatus, execute_command
from filesystem import FileSystemError, VirtualFileSystem
from main import main
from shell import run_script, run_shell


VALID_VFS = '{"name": "/", "type": "directory", "owner": "root", "children": {}}'


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
        input_stream = io.StringIO('ls /home\nunknown\nls "unfinished\n\nexit\n')
        output_stream = io.StringIO()
        filesystem = VirtualFileSystem.load(
            Path(__file__).parents[1] / "data/vfs_sample.json"
        )

        run_shell(input_stream, output_stream, filesystem=filesystem)

        output = output_stream.getvalue()
        self.assertIn("my_vfs:/$ ", output)
        self.assertIn("student", output)
        self.assertIn("readme.txt", output)
        self.assertIn("Ошибка: неизвестная команда: unknown", output)
        self.assertIn("Ошибка: незакрытая кавычка", output)
        self.assertNotIn("Traceback", output)

    def test_script_echoes_commands_and_stops_on_first_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "commands.txt"
            script_path.write_text("\nls /home\nunknown\nexit\n", encoding="utf-8")
            output_stream = io.StringIO()
            filesystem = VirtualFileSystem.load(
                Path(__file__).parents[1] / "data/vfs_sample.json"
            )

            status = run_script(str(script_path), "demo", output_stream, filesystem)

        self.assertIs(status, CommandStatus.ERROR)
        output = output_stream.getvalue()
        self.assertIn("demo:/$ ls /home", output)
        self.assertIn("student", output)
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
            vfs_path.write_text(VALID_VFS, encoding="utf-8")
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
            vfs_path.write_text(VALID_VFS, encoding="utf-8")
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
            vfs_path.write_text(VALID_VFS, encoding="utf-8")
            script_path.write_text("unknown\n", encoding="utf-8")
            output_stream = io.StringIO()
            error_stream = io.StringIO()

            with patch("sys.stdout", output_stream), patch("sys.stderr", error_stream):
                status = main(["--vfs", str(vfs_path), "--script", str(script_path)])

        self.assertEqual(status, 1)
        self.assertIn("Ошибка: неизвестная команда: unknown", output_stream.getvalue())
        self.assertEqual(output_stream.getvalue().count("sample:/$ "), 1)


class VirtualFileSystemTests(unittest.TestCase):
    def test_loads_valid_vfs_and_resolves_absolute_and_relative_paths(self) -> None:
        filesystem = VirtualFileSystem.load(Path(__file__).parents[1] / "data/vfs_sample.json")
        filesystem.change_directory("/home/student")

        self.assertEqual(filesystem.resolve("notes.txt")["content"], "First line\nSecond line\n")
        self.assertEqual(
            filesystem.resolve("../readme.txt")["content"],
            "Sample virtual filesystem.\n",
        )
        self.assertEqual(filesystem.resolve("/home/student")["type"], "directory")
        self.assertEqual(filesystem.resolve(".")["name"], "student")

    def test_rejects_paths_above_root(self) -> None:
        filesystem = VirtualFileSystem.load(Path(__file__).parents[1] / "vfs.json")
        with self.assertRaisesRegex(FileSystemError, "выше корня"):
            filesystem.resolve("../home")

    def test_load_errors_are_clear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "missing.json"
            with self.assertRaisesRegex(FileSystemError, "не найден"):
                VirtualFileSystem.load(missing_path)

            malformed_path = Path(directory) / "malformed.json"
            malformed_path.write_text('{"name":', encoding="utf-8")
            with self.assertRaisesRegex(FileSystemError, "не удалось прочитать VFS"):
                VirtualFileSystem.load(malformed_path)

            missing_fields_path = Path(directory) / "missing-fields.json"
            missing_fields_path.write_text('{"name": "/"}', encoding="utf-8")
            with self.assertRaisesRegex(FileSystemError, "отсутствует поле"):
                VirtualFileSystem.load(missing_fields_path)

            unknown_type_path = Path(directory) / "unknown-type.json"
            unknown_type_path.write_text(
                '{"name": "/", "type": "directory", "owner": "root", '
                '"children": {"item": {"name": "item", "type": "socket", "owner": "root"}}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileSystemError, "неизвестный тип"):
                VirtualFileSystem.load(unknown_type_path)

            invalid_root_path = Path(directory) / "invalid-root.json"
            invalid_root_path.write_text(
                '{"name": "/", "type": "file", "owner": "root", "content": "not a root"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileSystemError, "корень VFS"):
                VirtualFileSystem.load(invalid_root_path)

    def test_save_and_reload_preserves_vfs(self) -> None:
        filesystem = VirtualFileSystem.load(Path(__file__).parents[1] / "data/vfs_sample.json")
        with tempfile.TemporaryDirectory() as directory:
            saved_path = Path(directory) / "saved.json"
            filesystem.save(saved_path)
            reloaded = VirtualFileSystem.load(saved_path)

        self.assertEqual(reloaded.root, filesystem.root)

    def test_reset_restores_project_default_without_writing_to_disk(self) -> None:
        source_path = Path(__file__).parents[1] / "data/vfs_sample.json"
        original_contents = source_path.read_text(encoding="utf-8")
        filesystem = VirtualFileSystem.load(source_path)
        filesystem.current_directory = "/home"
        filesystem.root["children"]["temporary"] = {
            "name": "temporary",
            "type": "file",
            "owner": "student",
            "content": "not saved",
        }

        filesystem.reset()

        self.assertEqual(filesystem.root["children"], {})
        self.assertEqual(filesystem.current_directory, "/")
        self.assertEqual(source_path.read_text(encoding="utf-8"), original_contents)

    def test_vfs_commands_save_and_reset(self) -> None:
        filesystem = VirtualFileSystem.load(Path(__file__).parents[1] / "data/vfs_sample.json")
        output_stream = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "command-saved.json"
            status = execute_command("vfs-save", [str(save_path)], output_stream, filesystem)
            self.assertIs(status, CommandStatus.CONTINUE)
            self.assertTrue(save_path.is_file())

        filesystem.root["children"].clear()
        status = execute_command("vfs-init", [], output_stream, filesystem)

        self.assertIs(status, CommandStatus.CONTINUE)
        self.assertEqual(filesystem.root["children"], {})
        self.assertIn("VFS сохранена", output_stream.getvalue())
        self.assertIn("VFS сброшена", output_stream.getvalue())

    def test_main_reports_invalid_vfs_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid_path = Path(directory) / "invalid.json"
            invalid_path.write_text("{", encoding="utf-8")
            output_stream = io.StringIO()
            error_stream = io.StringIO()

            with patch("sys.stdout", output_stream), patch("sys.stderr", error_stream):
                status = main(["--vfs", str(invalid_path)])

        self.assertEqual(status, 1)
        self.assertIn("не удалось прочитать VFS", error_stream.getvalue())
        self.assertNotIn("Traceback", error_stream.getvalue())


class BasicFileSystemCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.filesystem = VirtualFileSystem.load(
            Path(__file__).parents[1] / "data/vfs_sample.json"
        )
        self.output = io.StringIO()

    def run_command(self, command: str, *arguments: str) -> CommandStatus:
        return execute_command(command, arguments, self.output, self.filesystem)

    def test_ls_shows_current_or_requested_directory(self) -> None:
        status = self.run_command("ls")
        self.assertIs(status, CommandStatus.CONTINUE)
        self.assertEqual(self.output.getvalue().splitlines(), ["home", "tmp"])

        self.output = io.StringIO()
        status = self.run_command("ls", "/home/student")
        self.assertIs(status, CommandStatus.CONTINUE)
        self.assertEqual(self.output.getvalue().splitlines(), ["notes.txt", "duplicates.txt"])

    def test_ls_reports_missing_path_and_file(self) -> None:
        self.assertIs(self.run_command("ls", "/missing"), CommandStatus.ERROR)
        self.assertIn("путь не найден", self.output.getvalue())

        self.output = io.StringIO()
        self.assertIs(self.run_command("ls", "/home/readme.txt"), CommandStatus.ERROR)
        self.assertIn("это не директория", self.output.getvalue())

    def test_cd_changes_path_and_default_returns_to_root(self) -> None:
        self.assertIs(self.run_command("cd", "/home/student"), CommandStatus.CONTINUE)
        self.assertEqual(self.filesystem.current_directory, "/home/student")

        self.assertIs(self.run_command("cd", ".."), CommandStatus.CONTINUE)
        self.assertEqual(self.filesystem.current_directory, "/home")

        self.assertIs(self.run_command("cd"), CommandStatus.CONTINUE)
        self.assertEqual(self.filesystem.current_directory, "/")

    def test_cd_rejects_files_and_paths_above_root(self) -> None:
        self.assertIs(self.run_command("cd", "/home/readme.txt"), CommandStatus.ERROR)
        self.assertIn("это не директория", self.output.getvalue())

        self.output = io.StringIO()
        self.assertIs(self.run_command("cd", ".."), CommandStatus.ERROR)
        self.assertIn("выше корня", self.output.getvalue())
        self.assertEqual(self.filesystem.current_directory, "/")

    def test_pwd_prints_full_current_path(self) -> None:
        self.filesystem.change_directory("/home/student")
        self.assertIs(self.run_command("pwd"), CommandStatus.CONTINUE)
        self.assertEqual(self.output.getvalue(), "/home/student\n")

    def test_uniq_removes_only_adjacent_duplicate_lines(self) -> None:
        source = self.filesystem.resolve("/home/student/duplicates.txt")
        original_content = source["content"]

        status = self.run_command("uniq", "/home/student/duplicates.txt")

        self.assertIs(status, CommandStatus.CONTINUE)
        self.assertEqual(self.output.getvalue(), "apple\nbanana\napple\n")
        self.assertEqual(source["content"], original_content)

    def test_uniq_reports_missing_paths_and_directories(self) -> None:
        self.assertIs(self.run_command("uniq", "/missing.txt"), CommandStatus.ERROR)
        self.assertIn("путь не найден", self.output.getvalue())

        self.output = io.StringIO()
        self.assertIs(self.run_command("uniq", "/home"), CommandStatus.ERROR)
        self.assertIn("это не файл", self.output.getvalue())

    def test_clear_writes_terminal_escape_sequence_only_to_terminal(self) -> None:
        class TerminalOutput(io.StringIO):
            def isatty(self) -> bool:
                return True

        terminal = TerminalOutput()
        self.assertIs(
            execute_command("clear", [], terminal, self.filesystem),
            CommandStatus.CONTINUE,
        )
        self.assertEqual(terminal.getvalue(), "\033[2J\033[H")

        self.assertIs(self.run_command("clear"), CommandStatus.CONTINUE)
        self.assertEqual(self.output.getvalue(), "")

    def test_wrong_argument_counts_are_reported(self) -> None:
        for command, arguments in (
            ("ls", ("/", "/home")),
            ("cd", ("/", "/home")),
            ("pwd", ("/",)),
            ("uniq", ()),
            ("uniq", ("/home", "/home")),
        ):
            with self.subTest(command=command, arguments=arguments):
                self.output = io.StringIO()
                self.assertIs(self.run_command(command, *arguments), CommandStatus.ERROR)
                self.assertIn("использование", self.output.getvalue())

    def test_demo_script_exercises_commands_and_stops_at_error(self) -> None:
        script_path = Path(__file__).parents[1] / "scripts/demo_basic_commands.txt"
        output = io.StringIO()

        status = run_script(
            str(script_path),
            "sample",
            output,
            self.filesystem,
        )

        self.assertIs(status, CommandStatus.ERROR)
        result = output.getvalue()
        self.assertIn("sample:/$ ls", result)
        self.assertIn("sample:/home/student$ pwd", result)
        self.assertIn("/home/student", result)
        self.assertIn("apple\nbanana\napple\n", result)
        self.assertIn("Ошибка:", result)
        self.assertNotIn("sample:/$ exit", result)


if __name__ == "__main__":
    unittest.main()
