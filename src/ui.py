"""
Terminal User Interface with ANSI colors, tables, and interactive prompts.
"""

import os
import sys
from typing import List, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # Enable ANSI escape sequences in Windows Command Prompt and PowerShell
    os.system("")

from .models import CleanResult, Project, format_size


class Colors:
    """ANSI color codes for rich terminal styling."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Standard colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Backgrounds
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"


def print_banner():
    """Print an attractive header banner."""
    banner = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}╔════════════════════════════════════════════════════════════════════════════╗
║                     🚀 PROJECT CLEANER FOR DEVELOPERS                      ║
║     Flutter • Node • Python • PHP • Go • .NET • Gradle • Windows Caches    ║
╚════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def print_info(msg: str):
    print(f"{Colors.BRIGHT_BLUE}ℹ{Colors.RESET} {msg}")


def print_success(msg: str):
    print(f"{Colors.BRIGHT_GREEN}✔{Colors.RESET} {msg}")


def print_warning(msg: str):
    print(f"{Colors.BRIGHT_YELLOW}⚠{Colors.RESET} {msg}")


def print_error(msg: str):
    print(f"{Colors.BRIGHT_RED}✖{Colors.RESET} {msg}")


def type_badge(project_type: str, display_name: str) -> str:
    """Return a color-coded badge for the project type."""
    colors = {
        "flutter": Colors.BRIGHT_CYAN,
        "node": Colors.BRIGHT_GREEN,
        "python": Colors.BRIGHT_YELLOW,
        "php": Colors.BRIGHT_MAGENTA,
        "gradle": Colors.YELLOW,
        "dotnet": Colors.BRIGHT_BLUE,
        "golang": Colors.CYAN,
        "rust": Colors.BRIGHT_RED,
        "xcode": Colors.BLUE,
    }
    col = colors.get(project_type, Colors.WHITE)
    short_name = display_name.split("/")[0].strip()
    return f"{col}[{short_name}]{Colors.RESET}"


def display_project_table(
    projects: List[Project],
    title: str = "Discovered Projects & Cleanable Space",
    show_empty: bool = False,
):
    """Render a clean, formatted table of projects and their cleanable targets."""
    filtered_projects = [p for p in projects if p.total_cleanable_bytes > 0] if not show_empty else projects

    if not filtered_projects:
        print_info("Tidak ada berkas cache / cleanable targets yang ditemukan.")
        return

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}📂 {title}:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 88}{Colors.RESET}")
    print(
        f" {Colors.BOLD}{'#':<4} {'PROJECT NAME':<24} {'TYPE':<16} {'CLEANABLE ITEMS':<28} {'SIZE':>12}{Colors.RESET}"
    )
    print(f"{Colors.DIM}{'─' * 88}{Colors.RESET}")

    total_bytes = 0
    # Determine if projects span multiple drives
    unique_drives = {p.path.drive for p in filtered_projects if p.path.drive}
    show_drive = len(unique_drives) > 1

    for idx, proj in enumerate(filtered_projects, 1):
        total_bytes += proj.total_cleanable_bytes
        
        # Format target items summary (e.g., "node_modules (1.2 GB), dist (50 MB)")
        target_summaries = []
        for t in proj.targets:
            if t.size_bytes > 0:
                target_summaries.append(f"{t.relative_to_project} ({t.formatted_size})")

        items_str = ", ".join(target_summaries) if target_summaries else "-"
        if len(items_str) > 28:
            items_str = items_str[:25] + "..."

        prefix = f"{proj.path.drive} " if show_drive and proj.path.drive else ""
        name_str = f"{prefix}{proj.name}"
        if len(name_str) > 23:
            name_str = name_str[:20] + "..."

        badge = type_badge(proj.project_type, proj.display_name)
        
        size_color = Colors.BRIGHT_GREEN if proj.total_cleanable_bytes > 500 * 1024 * 1024 else Colors.WHITE
        size_str = f"{size_color}{proj.formatted_total_size:>12}{Colors.RESET}"

        print(
            f" {Colors.CYAN}{idx:<4}{Colors.RESET} {Colors.BOLD}{name_str:<24}{Colors.RESET} {badge:<25} {items_str:<28} {size_str}"
        )

    print(f"{Colors.DIM}{'─' * 88}{Colors.RESET}")
    total_str = format_size(total_bytes)
    print(
        f" {Colors.BOLD}Total Space to Reclaim: {Colors.BRIGHT_GREEN}{total_str}{Colors.RESET} across {len(filtered_projects)} project(s).\n"
    )


def print_clean_results(results_by_project: dict[str, CleanResult]):
    """Print the final summary of cleaning operations."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}✨ CLEANING SUMMARY:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

    total_freed = 0
    total_items = 0
    total_errors = 0

    for proj_name, res in results_by_project.items():
        total_freed += res.freed_bytes
        total_items += len(res.deleted_items)
        total_errors += len(res.failed_items)

        items_detail = ", ".join(res.deleted_items)
        if len(items_detail) > 40:
            items_detail = items_detail[:37] + "..."

        status_icon = f"{Colors.BRIGHT_GREEN}✔{Colors.RESET}" if not res.failed_items else f"{Colors.BRIGHT_YELLOW}⚠{Colors.RESET}"
        print(f" {status_icon} {Colors.BOLD}{proj_name}{Colors.RESET}: freed {Colors.BRIGHT_GREEN}{res.formatted_freed}{Colors.RESET} ({len(res.deleted_items)} items)")

        for item, err in res.failed_items:
            print(f"   {Colors.RED}✖ Failed to remove {item}: {err}{Colors.RESET}")

    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
    print(
        f"{Colors.BOLD}🎉 Total Disk Space Freed: {Colors.BRIGHT_GREEN}{format_size(total_freed)}{Colors.RESET} | Items cleaned: {total_items}"
    )
    if total_errors > 0:
        print(f"{Colors.YELLOW}Perhatian: Ada {total_errors} item yang gagal dihapus.{Colors.RESET}")
    print()


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Ask user for yes/no confirmation with default."""
    hint = "[y/N]" if not default else "[Y/n]"
    try:
        ans = input(f"{Colors.BOLD}{Colors.BRIGHT_YELLOW}{prompt} {hint}: {Colors.RESET}").strip().lower()
        if not ans:
            return default
        return ans in {"y", "yes", "ya", "1"}
    except (KeyboardInterrupt, EOFError):
        print("\nDibatalkan.")
        return False
