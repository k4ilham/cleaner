"""
Configuration and constants for Project Cleaner.
"""

from pathlib import Path

# Common directory names to ignore during scanning
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "Library",
    "Applications",
    "System",
    ".Trash",
    "Trash",
    "Music",
    "Pictures",
    "Movies",
    ".vscode",
    ".idea",
    ".cursor",
    # Windows-specific system and reserved directories
    "$RECYCLE.BIN",
    "$Recycle.Bin",
    "System Volume Information",
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "AppData",
    "Recovery",
    "PerfLogs",
    "msdownld.tmp",
}

# Max scan depth by default
DEFAULT_SCAN_DEPTH = 4

# Known project markers and their cleanable targets
PROJECT_DEFINITIONS = {
    "flutter": {
        "name": "Flutter / Dart",
        "markers": ["pubspec.yaml"],
        "targets": [
            "build",
            ".dart_tool",
            ".flutter-plugins",
            ".flutter-plugins-dependencies",
            "android/.gradle",
            "android/app/build",
            "ios/Pods",
            "ios/.symlinks",
        ],
        "command": ["flutter", "clean"],
    },
    "node": {
        "name": "Node.js / Web",
        "markers": ["package.json"],
        "targets": [
            "node_modules",
            ".next",
            ".nuxt",
            "dist",
            ".output",
            ".turbo",
            ".cache",
            ".parcel-cache",
            ".svelte-kit",
            ".astro",
            "coverage",
        ],
    },
    "python": {
        "name": "Python",
        "markers": [
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "Pipfile",
            "environment.yml",
        ],
        "targets": [
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".coverage",
            "htmlcov",
            ".tox",
            "build",
            "dist",
            "*.egg-info",
        ],
        "optional_targets": [
            ".venv",
            "venv",
            "env",
        ],
    },
    "gradle": {
        "name": "Gradle / Android",
        "markers": ["build.gradle", "build.gradle.kts", "settings.gradle"],
        "targets": [
            ".gradle",
            "build",
            "app/build",
        ],
    },
    "xcode": {
        "name": "Xcode / iOS / macOS",
        "markers": ["Podfile", "Package.swift"],
        "glob_markers": ["*.xcodeproj", "*.xcworkspace"],
        "targets": [
            "Pods",
            "DerivedData",
            ".build",
        ],
    },
    "rust": {
        "name": "Rust / Cargo",
        "markers": ["Cargo.toml"],
        "targets": [
            "target",
        ],
        "command": ["cargo", "clean"],
    },
    "php": {
        "name": "PHP / Laravel / Composer",
        "markers": ["composer.json"],
        "targets": [
            "storage/logs",
            "storage/framework/cache",
            "storage/framework/views",
            "storage/framework/sessions",
            "bootstrap/cache",
            ".phpunit.cache",
            "var/cache",
        ],
        "optional_targets": [
            "vendor",
        ],
    },
    "golang": {
        "name": "Go / Golang",
        "markers": ["go.mod"],
        "targets": [
            "bin",
            "dist",
            "tmp",
            ".air_tmp",
        ],
        "command": ["go", "clean"],
    },
    "dotnet": {
        "name": ".NET / C#",
        "markers": ["*.sln", "*.csproj", "*.fsproj"],
        "targets": [
            "bin",
            "obj",
            ".vs",
            "TestResults",
        ],
        "command": ["dotnet", "clean"],
    },
}
