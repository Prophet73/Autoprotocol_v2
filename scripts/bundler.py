"""
WhisperX Pipeline - Code Bundler
Собирает кодовую базу проекта в один текстовый файл для анализа.
Использует git для определения tracked файлов, игнорирует мусорные файлы.
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

# --- НАСТРОЙКИ ---
# Корневая папка проекта (где находится .git)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Папка для сохранения bundle файлов
OUTPUT_DIR = PROJECT_ROOT / "scripts" / "bundles"

# Имя выходного файла (с timestamp)
OUTPUT_FILENAME = f"codebase_bundle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

# Разрешенные расширения файлов (релевантные для проекта)
ALLOWED_EXTENSIONS = {
    # Backend Python
    ".py",          # Python код
    ".pyi",         # Python type stubs
    ".toml",        # pyproject.toml
    ".ini",         # alembic.ini, configs
    ".cfg",         # setup.cfg

    # Frontend (если появится)
    ".js", ".jsx",  # JavaScript
    ".ts", ".tsx",  # TypeScript
    ".vue",         # Vue.js
    ".json",        # package.json, configs
    ".css",         # Стили
    ".scss", ".sass",
    ".html",        # HTML templates

    # DevOps
    ".yml", ".yaml",    # Docker Compose, CI/CD
    ".dockerfile",      # Dockerfile
    ".sh",              # Shell scripts
    ".ps1",             # PowerShell scripts
    ".bat",             # Batch scripts

    # Документация
    ".md",          # Markdown

    # Конфиги
    ".gitignore",
    ".editorconfig",
    ".dockerignore",
}

# Файлы без расширения или с особыми именами
ALLOWED_FILENAMES = {
    "Dockerfile",
    "Makefile",
    ".env.example",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-extra.txt",
    "requirements-docker.txt",
    "setup.py",
    "CLAUDE.md",
}

# Игнорируемые папки (даже если в git)
IGNORED_DIR_NAMES = {
    # Python
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".venv", "venv", "env",
    "dist", "build",
    ".eggs",
    "*.egg-info",

    # Node
    "node_modules",

    # Project specific
    "output",           # Результаты транскрипции
    "bundles",          # Выходные bundle файлы
    "legacy",           # Устаревшие скрипты
    ".playwright-mcp",  # Playwright временные файлы

    # IDE
    ".idea",
    ".vscode",
}

# Игнорируемые паттерны/суффиксы файлов
IGNORED_FILE_PATTERNS = {
    # Python compiled
    ".pyc", ".pyo", ".pyd",

    # Libraries
    ".so", ".dll", ".dylib",
    ".egg-info",

    # Logs
    ".log",

    # Databases
    ".db", ".sqlite", ".sqlite3",

    # Secrets (ВАЖНО!)
    ".env",

    # System
    ".DS_Store",
    "Thumbs.db",
    ".coverage",

    # Minified
    ".min.js",
    ".min.css",

    # Media (WhisperX specific)
    ".mp4", ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".avi", ".mkv",
    ".mov", ".wmv", ".aac", ".wma",

    # Documents (output files)
    ".docx", ".doc", ".pdf", ".xlsx", ".xls",

    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",

    # Archives
    ".zip", ".tar", ".gz", ".rar", ".7z",

    # Models/weights
    ".pt", ".pth", ".onnx", ".bin", ".safetensors",
}

# Игнорируемые имена файлов
IGNORED_FILENAMES = {
    "package-lock.json",
    "poetry.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "uv.lock",
    "nul",               # Windows null file
}

# Максимальный размер файла в байтах (5 MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

# --- КОНЕЦ НАСТРОЕК ---


def get_git_tracked_files(include_untracked: bool = False) -> List[Path]:
    """
    Получает список файлов из git.

    Args:
        include_untracked: Также включить untracked файлы (новые, не добавленные в git)

    Returns:
        List[Path]: Список путей к файлам
    """
    files = []

    try:
        # Tracked files
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.strip().split('\n'):
            if line:
                file_path = PROJECT_ROOT / line
                if file_path.exists() and file_path.is_file():
                    files.append(file_path)

        tracked_count = len(files)
        print(f"    Tracked файлов: {tracked_count}")

        # Untracked files (новые, еще не добавленные в git)
        if include_untracked:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True
            )

            untracked_count = 0
            for line in result.stdout.strip().split('\n'):
                if line:
                    file_path = PROJECT_ROOT / line
                    if file_path.exists() and file_path.is_file():
                        files.append(file_path)
                        untracked_count += 1

            print(f"    Untracked файлов: {untracked_count}")

        return files

    except subprocess.CalledProcessError:
        print("  Git не доступен или это не git репозиторий.")
        print("Используйте git init для инициализации репозитория.")
        return []
    except FileNotFoundError:
        print("  Git не установлен в системе.")
        return []


def should_include_file(file_path: Path) -> bool:
    """
    Проверяет, должен ли файл быть включен в bundle.

    Args:
        file_path: Путь к файлу

    Returns:
        bool: True если файл нужно включить
    """
    # Проверка размера файла
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return False
    except OSError:
        return False

    # Проверка имени файла (игнорируемые)
    if file_path.name in IGNORED_FILENAMES:
        return False

    # Проверка паттернов файлов
    file_name_lower = file_path.name.lower()
    file_suffix_lower = file_path.suffix.lower()

    for pattern in IGNORED_FILE_PATTERNS:
        if pattern.startswith('*'):
            if file_name_lower.endswith(pattern[1:]):
                return False
        elif pattern.startswith('.'):
            if file_suffix_lower == pattern:
                return False
        elif file_name_lower.endswith(pattern):
            return False

    # Проверка директорий
    for part in file_path.parts:
        if part in IGNORED_DIR_NAMES:
            return False

    # Проверка разрешенных имен файлов
    if file_path.name in ALLOWED_FILENAMES:
        return True

    # Проверка расширения
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    return True


def get_relative_path(file_path: Path) -> str:
    """
    Получает относительный путь файла от корня проекта.

    Args:
        file_path: Абсолютный путь к файлу

    Returns:
        str: Относительный путь
    """
    try:
        return str(file_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(file_path)


def create_bundle(use_git: bool = True, include_untracked: bool = True, verbose: bool = False):
    """
    Создает bundle файл с кодовой базой проекта.

    Args:
        use_git: Использовать git для получения списка файлов
        include_untracked: Включить файлы, не добавленные в git (новые файлы)
        verbose: Показывать исключённые файлы
    """
    print("=" * 80)
    print("WhisperX Pipeline - Code Bundler")
    print("=" * 80)

    # Создаем выходную директорию
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = OUTPUT_DIR / OUTPUT_FILENAME

    # Получаем список файлов
    if use_git:
        print("\n[*] Получаю список файлов из git...")
        if include_untracked:
            print("    (включая untracked файлы)")
        all_files = get_git_tracked_files(include_untracked=include_untracked)
        if not all_files:
            print("[!] Не удалось получить список файлов из git.")
            return
    else:
        print("\n[*] Сканирую файловую систему...")
        all_files = []
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Удаляем игнорируемые директории
            dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES and not d.startswith('.')]

            for filename in files:
                file_path = Path(root) / filename
                all_files.append(file_path)

    print(f"    Всего файлов: {len(all_files)}")

    # Фильтруем файлы
    print("\n[*] Фильтрую файлы...")
    filtered_files = []
    excluded_files = []

    for f in all_files:
        if should_include_file(f):
            filtered_files.append(f)
        else:
            excluded_files.append(f)

    print(f"    Отобрано для bundle: {len(filtered_files)}")
    print(f"    Исключено: {len(excluded_files)}")

    if verbose and excluded_files:
        print("\n    Исключённые файлы:")
        for f in excluded_files[:20]:  # Показываем первые 20
            print(f"      - {get_relative_path(f)}")
        if len(excluded_files) > 20:
            print(f"      ... и ещё {len(excluded_files) - 20} файлов")

    # Группируем файлы по директориям для лучшей организации
    filtered_files.sort(key=lambda x: (str(x.parent), x.name))

    # Записываем bundle
    print(f"\n[*] Создаю bundle файл: {output_file_path.name}")

    try:
        with open(output_file_path, "w", encoding="utf-8") as outfile:
            # Заголовок
            outfile.write("=" * 100 + "\n")
            outfile.write("WHISPERX PIPELINE - CODE BUNDLE\n")
            outfile.write("=" * 100 + "\n")
            outfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write(f"Project Root: {PROJECT_ROOT}\n")
            outfile.write(f"Total Files: {len(filtered_files)}\n")
            outfile.write(f"Git Tracked: {'Yes' if use_git else 'No'}\n")
            outfile.write("=" * 100 + "\n\n")

            # Оглавление
            outfile.write("TABLE OF CONTENTS\n")
            outfile.write("-" * 100 + "\n")
            for idx, file_path in enumerate(filtered_files, 1):
                rel_path = get_relative_path(file_path)
                outfile.write(f"{idx:4d}. {rel_path}\n")
            outfile.write("\n" + "=" * 100 + "\n\n")

            # Содержимое файлов
            current_dir = None

            for idx, file_path in enumerate(filtered_files, 1):
                rel_path = get_relative_path(file_path)

                # Показываем прогресс
                if idx % 10 == 0:
                    print(f"    Обработано: {idx}/{len(filtered_files)}")

                # Заголовок директории (если изменилась)
                try:
                    file_dir = str(file_path.parent.relative_to(PROJECT_ROOT))
                except ValueError:
                    file_dir = str(file_path.parent)

                if file_dir != current_dir:
                    current_dir = file_dir
                    outfile.write("\n" + "#" * 100 + "\n")
                    outfile.write(f"# DIRECTORY: {file_dir}\n")
                    outfile.write("#" * 100 + "\n\n")

                # Заголовок файла
                outfile.write(f"\n{'=' * 100}\n")
                outfile.write(f"FILE [{idx}/{len(filtered_files)}]: {rel_path}\n")
                outfile.write(f"Size: {file_path.stat().st_size} bytes\n")
                outfile.write(f"{'=' * 100}\n\n")

                # Содержимое файла
                try:
                    with open(file_path, "r", encoding="utf-8") as infile:
                        content = infile.read()
                        outfile.write(content)

                        # Добавляем перевод строки, если файл не заканчивается на него
                        if content and not content.endswith('\n'):
                            outfile.write('\n')

                except UnicodeDecodeError:
                    # Попытка прочитать в другой кодировке
                    try:
                        with open(file_path, "r", encoding="latin-1") as infile:
                            content = infile.read()
                            outfile.write("[WARNING: File read with latin-1 encoding]\n\n")
                            outfile.write(content)
                    except Exception as e:
                        outfile.write(f"[ERROR: Could not read file: {e}]\n")

                except Exception as e:
                    outfile.write(f"[ERROR: {e}]\n")

                outfile.write(f"\n{'=' * 100}\n")
                outfile.write(f"END OF FILE: {rel_path}\n")
                outfile.write(f"{'=' * 100}\n\n")

            # Футер
            outfile.write("\n" + "=" * 100 + "\n")
            outfile.write("END OF BUNDLE\n")
            outfile.write(f"Total Files Bundled: {len(filtered_files)}\n")
            outfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write("=" * 100 + "\n")

        # Информация о результате
        file_size_kb = output_file_path.stat().st_size / 1024
        file_size_mb = file_size_kb / 1024

        print("\n" + "=" * 80)
        print("[+] Bundle успешно создан!")
        print("=" * 80)
        print(f"    Файл: {output_file_path}")
        if file_size_mb >= 1:
            print(f"    Размер: {file_size_mb:.2f} MB")
        else:
            print(f"    Размер: {file_size_kb:.2f} KB")
        print(f"    Файлов: {len(filtered_files)}")
        print("=" * 80)

    except IOError as e:
        print(f"\n[!] Ошибка записи в файл: {e}")
    except Exception as e:
        print(f"\n[!] Непредвиденная ошибка: {e}")


def main():
    """Главная функция."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Собирает кодовую базу WhisperX Pipeline в один текстовый файл"
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Не использовать git, сканировать файловую систему"
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Только tracked файлы (без новых untracked)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Показать исключённые файлы"
    )

    args = parser.parse_args()

    create_bundle(
        use_git=not args.no_git,
        include_untracked=not args.tracked_only,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
