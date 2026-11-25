import copy
import json
from pathlib import Path
from typing import Any


DEFAULT_VFS_PATH = Path(__file__).with_name("vfs.json")


class FileSystemError(Exception):
    pass


class VirtualFileSystem:
    def __init__(self, root: dict[str, Any], default_root: dict[str, Any]) -> None:
        self.root = root
        self._default_root = default_root
        self.current_directory = "/"

    @classmethod
    def load(cls, path: str | Path) -> "VirtualFileSystem":
        vfs_path = Path(path)
        root = cls._read_vfs(vfs_path)

        if vfs_path.resolve() == DEFAULT_VFS_PATH.resolve():
            default_root = copy.deepcopy(root)
        else:
            default_root = cls._read_vfs(DEFAULT_VFS_PATH)

        return cls(root, default_root)

    @classmethod
    def _read_vfs(cls, path: Path) -> dict[str, Any]:
        try:
            with path.open(encoding="utf-8") as file:
                root = json.load(file)
        except FileNotFoundError as error:
            raise FileSystemError(f"файл VFS не найден: {path}") from error
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise FileSystemError(f"не удалось прочитать VFS {path}: {error}") from error

        cls._validate_node(root, "/", is_root=True)
        return root

    @classmethod
    def _validate_node(
        cls,
        node: Any,
        expected_name: str,
        *,
        is_root: bool = False,
    ) -> None:
        if not isinstance(node, dict):
            raise FileSystemError(f"объект {expected_name!r} должен быть JSON-объектом")

        for field in ("name", "type", "owner"):
            if field not in node:
                raise FileSystemError(f"у объекта {expected_name!r} отсутствует поле {field!r}")

        if not isinstance(node["name"], str) or node["name"] != expected_name:
            raise FileSystemError(f"неверное имя объекта {expected_name!r}")
        if not isinstance(node["owner"], str):
            raise FileSystemError(f"поле owner объекта {expected_name!r} должно быть строкой")

        node_type = node["type"]
        if is_root and node_type != "directory":
            raise FileSystemError("корень VFS должен иметь тип directory")
        if node_type == "file":
            if "content" not in node or not isinstance(node["content"], str):
                raise FileSystemError(
                    f"у файла {expected_name!r} должно быть строковое поле content"
                )
            return

        if node_type != "directory":
            raise FileSystemError(
                f"неизвестный тип объекта {expected_name!r}: {node_type!r}"
            )
        if "children" not in node or not isinstance(node["children"], dict):
            raise FileSystemError(
                f"у директории {expected_name!r} должно быть поле children-объект"
            )
        if is_root and expected_name != "/":
            raise FileSystemError("корневая директория VFS должна называться '/'")

        for child_name, child in node["children"].items():
            if (
                not isinstance(child_name, str)
                or not child_name
                or child_name in {".", ".."}
                or "/" in child_name
            ):
                raise FileSystemError(f"недопустимое имя объекта: {child_name!r}")
            cls._validate_node(child, child_name)

    def resolve(self, path: str) -> dict[str, Any]:
        if not isinstance(path, str):
            raise FileSystemError("путь должен быть строкой")

        components = [] if path.startswith("/") else self._current_components()
        for component in path.split("/"):
            if component in {"", "."}:
                continue
            if component == "..":
                if not components:
                    raise FileSystemError("нельзя перейти выше корня VFS")
                components.pop()
                continue

            directory = self._find_directory(components)
            children = directory["children"]
            if component not in children:
                raise FileSystemError(f"путь не найден: {path}")
            components.append(component)

        return self._find_node(components)

    def change_directory(self, path: str) -> None:
        node = self.resolve(path)
        if node["type"] != "directory":
            raise FileSystemError(f"это не директория: {path}")
        self.current_directory = self._format_path(self._resolve_components(path))

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        try:
            with destination.open("w", encoding="utf-8") as file:
                json.dump(self.root, file, ensure_ascii=False, indent=4)
                file.write("\n")
        except (OSError, UnicodeError) as error:
            raise FileSystemError(f"не удалось сохранить VFS в {destination}: {error}") from error

    def reset(self) -> None:
        self.root = copy.deepcopy(self._default_root)
        self.current_directory = "/"

    def _current_components(self) -> list[str]:
        if self.current_directory == "/":
            return []
        return self.current_directory.strip("/").split("/")

    def _resolve_components(self, path: str) -> list[str]:
        components = [] if path.startswith("/") else self._current_components()
        for component in path.split("/"):
            if component in {"", "."}:
                continue
            if component == "..":
                if not components:
                    raise FileSystemError("нельзя перейти выше корня VFS")
                components.pop()
            else:
                self._find_directory(components)
                components.append(component)
        return components

    def _find_directory(self, components: list[str]) -> dict[str, Any]:
        node = self._find_node(components)
        if node["type"] != "directory":
            raise FileSystemError(f"это не директория: {self._format_path(components)}")
        return node

    def _find_node(self, components: list[str]) -> dict[str, Any]:
        node = self.root
        for component in components:
            if node["type"] != "directory":
                raise FileSystemError(f"это не директория: {self._format_path(components)}")
            try:
                node = node["children"][component]
            except KeyError as error:
                raise FileSystemError(
                    f"путь не найден: {self._format_path(components)}"
                ) from error
        return node

    @staticmethod
    def _format_path(components: list[str]) -> str:
        return "/" + "/".join(components) if components else "/"
