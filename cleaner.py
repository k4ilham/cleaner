#!/usr/bin/env python3
"""
Project Cleaner - CLI and Interactive Tool to clean developer projects and system caches.
Supports Flutter, Node.js, Python, PHP/Laravel, Go, .NET/C#, Gradle/Android, Xcode/iOS, Rust,
and Windows / macOS System Caches across multiple drives (Drive C:, D:, etc.).
Logs all deleted files and freed space to a .log file.
"""

import argparse
import os
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.system("")

# Ensure current package can be imported
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.cleaners import get_all_cleaners, get_cleaners_dict
from src.cleaners.base import BaseCleaner
from src.logger import CleanerLogger
from src.models import CleanResult, CleanTarget, Project, format_size
from src.scanner import ProjectScanner
from src.system_cleaner import (
    SystemCacheItem,
    clean_system_cache_item,
    scan_system_caches,
)
from src.ui import (
    Colors,
    confirm_action,
    display_project_table,
    print_banner,
    print_clean_results,
    print_error,
    print_info,
    print_success,
    print_warning,
)


def get_available_drives() -> List[Path]:
    """Detect all mounted drives on Windows or root on Unix."""
    if platform.system() == "Windows":
        drives = []
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            p = Path(f"{letter}:/")
            if p.exists():
                drives.append(p)
        return drives
    return [Path("/")]


def parse_index_selection(input_str: str, max_val: int) -> List[int]:
    """Parse comma-separated or range selections (e.g. '1, 3, 5-7')."""
    selected = set()
    parts = [p.strip() for p in input_str.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2 and bounds[0].strip().isdigit() and bounds[1].strip().isdigit():
                start, end = int(bounds[0].strip()), int(bounds[1].strip())
                for i in range(start, end + 1):
                    if 1 <= i <= max_val:
                        selected.add(i - 1)
        elif part.isdigit():
            val = int(part)
            if 1 <= val <= max_val:
                selected.add(val - 1)
    return sorted(list(selected))


def execute_cleaning_batch(
    projects_to_clean: List[Project],
    cleaners_map: Dict[str, BaseCleaner],
    dry_run: bool = False,
    use_trash: bool = False,
    min_size_bytes: int = 0,
) -> Dict[str, CleanResult]:
    """Execute cleaning on selected projects."""
    results: Dict[str, CleanResult] = {}

    for proj in projects_to_clean:
        cleaner = cleaners_map.get(proj.project_type)
        if not cleaner:
            continue

        active_targets = [
            t for t in proj.targets if t.size_bytes >= min_size_bytes and (t.path.exists() or t.path.is_symlink())
        ]

        if not active_targets and not (cleaner.key == "flutter" and proj.has_clean_command):
            continue

        print(f"🧹 Membersihkan {Colors.BOLD}{proj.name}{Colors.RESET} ({proj.display_name})...")
        res = cleaner.execute_clean(
            project=proj,
            targets=active_targets,
            dry_run=dry_run,
            use_trash=use_trash,
            prefer_cli=True,
        )
        results[proj.name] = res

    return results


def handle_system_cache_menu(logger: CleanerLogger, use_trash: bool = False):
    """Submenu for scanning and cleaning system and developer global caches."""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}⚙️ MEMINDAI CACHE GLOBAL SISTEM & DEVELOPER...{Colors.RESET}")
    items = scan_system_caches()
    if not items:
        print_info("Tidak ada cache sistem berukuran besar yang ditemukan.")
        input(f"{Colors.DIM}Tekan Enter untuk kembali...{Colors.RESET}")
        return

    total_sys_bytes = sum(i.size_bytes for i in items)

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}Daftar Cache Global & Aplikasi Ditemukan:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
    print(f" {'#':<4} {'NAMA CACHE':<28} {'KATEGORI':<20} {'UKURAN':>12}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")

    for idx, item in enumerate(items, 1):
        print(f" {Colors.CYAN}{idx:<4}{Colors.RESET} {Colors.BOLD}{item.name:<28}{Colors.RESET} {item.category:<20} {Colors.BRIGHT_GREEN}{item.formatted_size:>12}{Colors.RESET}")
        print(f"      {Colors.DIM}Path: {item.path} ({item.description}){Colors.RESET}")

    print(f"{Colors.DIM}{'─' * 80}{Colors.RESET}")
    print(f" Total Cache: {Colors.BRIGHT_GREEN}{Colors.BOLD}{format_size(total_sys_bytes)}{Colors.RESET}\n")

    print("Pilihan:")
    print(" [1] Bersihkan SEMUA cache sistem di atas")
    print(" [2] Pilih nomor tertentu yang ingin dibersihkan (cth: 1, 3, 5)")
    print(" [b] Kembali ke menu utama")

    sub_choice = input(f"{Colors.BOLD}Pilihan Anda: {Colors.RESET}").strip().lower()
    if sub_choice == "b":
        return

    items_to_clean: List[SystemCacheItem] = []
    if sub_choice == "1":
        items_to_clean = items
    elif sub_choice == "2":
        sel_str = input(f"Masukkan nomor (1-{len(items)}): ").strip()
        indices = parse_index_selection(sel_str, len(items))
        items_to_clean = [items[i] for i in indices]
    else:
        print_error("Pilihan tidak valid.")
        return

    if not items_to_clean:
        print_warning("Tidak ada item yang dipilih.")
        return

    selected_bytes = sum(i.size_bytes for i in items_to_clean)
    trash_name = "Windows Recycle Bin" if platform.system() == "Windows" else "macOS Trash"
    target_action_desc = f"pindahkan ke {trash_name}" if use_trash else "HAPUS PERMANEN"
    if not confirm_action(f"Yakin ingin {target_action_desc} cache sebesar {format_size(selected_bytes)}?"):
        print("Pembersihan dibatalkan.")
        return

    print(f"\n{Colors.BOLD}Memulai pembersihan cache sistem...{Colors.RESET}")
    results_by_name: Dict[str, CleanResult] = {}

    for item in items_to_clean:
        print(f"🧹 Membersihkan {Colors.CYAN}{item.name}{Colors.RESET} ({item.formatted_size})...")
        res = clean_system_cache_item(item, dry_run=False, use_trash=use_trash)
        results_by_name[item.name] = res

    print_clean_results(results_by_name)
    logged_path = logger.log_session(
        target_dir=Path.home(),
        results_by_project=results_by_name,
        use_trash=use_trash,
        dry_run=False,
    )
    print_success(f"Catatan pembersihan sistem dicatat di: {Colors.BOLD}{logged_path}{Colors.RESET}")
    input(f"\n{Colors.DIM}Tekan Enter untuk kembali ke menu...{Colors.RESET}")


def run_interactive_menu(
    target_paths: Union[Path, List[Path]],
    include_venv: bool = False,
    max_depth: int = 4,
    ignore_dirs: Optional[Set[str]] = None,
    log_file: Optional[Path] = None,
):
    """Run full interactive terminal interface."""
    cleaners_map = get_cleaners_dict()
    use_trash = False
    logger = CleanerLogger(log_file)
    current_targets: List[Path] = [target_paths] if isinstance(target_paths, Path) else list(target_paths)

    while True:
        print_banner()
        is_multi_drive = len(current_targets) > 1
        targets_str = ", ".join(str(p.resolve()) for p in current_targets)
        print_info(f"Target Direktori : {Colors.BOLD}{targets_str}{Colors.RESET}")
        
        trash_name = "Recycle Bin (Tempat Sampah)" if platform.system() == "Windows" else "macOS Trash"
        trash_mode_text = (
            f"{Colors.BRIGHT_MAGENTA}{trash_name}{Colors.RESET}"
            if use_trash
            else f"{Colors.BRIGHT_RED}Permanent Delete{Colors.RESET}"
        )
        print_info(f"Mode Penghapusan : {trash_mode_text}")
        print_info(f"File Catatan Log : {Colors.CYAN}{logger.log_path}{Colors.RESET}")
        print(f"{Colors.DIM}Sedang memindai projek... mohon tunggu.{Colors.RESET}")

        scanner = ProjectScanner(
            cleaners=list(cleaners_map.values()),
            ignore_dirs=ignore_dirs,
            max_depth=max_depth,
            include_optional=include_venv,
        )

        if is_multi_drive:
            projects = scanner.scan_multiple(current_targets)
            table_title = f"Projek Ditemukan di Semua Drive ({', '.join(p.drive or str(p) for p in current_targets)})"
        else:
            projects = scanner.scan(current_targets[0])
            table_title = f"Projek Ditemukan di {current_targets[0]}"

        active_projects = [p for p in projects if p.total_cleanable_bytes > 0]
        display_project_table(projects, title=table_title)

        total_bytes = sum(p.total_cleanable_bytes for p in active_projects)
        flutter_projs = [p for p in active_projects if p.project_type == "flutter"]
        node_projs = [p for p in active_projects if p.project_type == "node"]
        python_projs = [p for p in active_projects if p.project_type == "python"]
        php_projs = [p for p in active_projects if p.project_type == "php"]
        gradle_projs = [p for p in active_projects if p.project_type == "gradle"]
        dotnet_projs = [p for p in active_projects if p.project_type == "dotnet"]
        golang_projs = [p for p in active_projects if p.project_type == "golang"]

        flutter_size = format_size(sum(p.total_cleanable_bytes for p in flutter_projs))
        node_size = format_size(sum(p.total_cleanable_bytes for p in node_projs))
        python_size = format_size(sum(p.total_cleanable_bytes for p in python_projs))
        php_size = format_size(sum(p.total_cleanable_bytes for p in php_projs))
        gradle_size = format_size(sum(p.total_cleanable_bytes for p in gradle_projs))
        dotnet_size = format_size(sum(p.total_cleanable_bytes for p in dotnet_projs))
        golang_size = format_size(sum(p.total_cleanable_bytes for p in golang_projs))

        print(f"{Colors.BOLD}{Colors.BRIGHT_WHITE}PILIHAN TINDAKAN:{Colors.RESET}")
        print(f" {Colors.CYAN}[1]{Colors.RESET} Bersihkan SEMUA projek ({Colors.BRIGHT_GREEN}{format_size(total_bytes)}{Colors.RESET})")
        print(f" {Colors.CYAN}[2]{Colors.RESET} Bersihkan projek FLUTTER ({len(flutter_projs)} projek, {Colors.BRIGHT_GREEN}{flutter_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[3]{Colors.RESET} Bersihkan projek NODE.JS ({len(node_projs)} projek, {Colors.BRIGHT_GREEN}{node_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[4]{Colors.RESET} Bersihkan cache PYTHON ({len(python_projs)} projek, {Colors.BRIGHT_GREEN}{python_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[5]{Colors.RESET} Bersihkan projek PHP / LARAVEL ({len(php_projs)} projek, {Colors.BRIGHT_GREEN}{php_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[6]{Colors.RESET} Bersihkan projek GRADLE / ANDROID ({len(gradle_projs)} projek, {Colors.BRIGHT_GREEN}{gradle_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[7]{Colors.RESET} Bersihkan projek .NET / C# ({len(dotnet_projs)} projek, {Colors.BRIGHT_GREEN}{dotnet_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[8]{Colors.RESET} Bersihkan projek GO / GOLANG ({len(golang_projs)} projek, {Colors.BRIGHT_GREEN}{golang_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[9]{Colors.RESET} Pilih projek tertentu berdasarkan nomor (cth: 1, 3, 5-8)")
        print(f" {Colors.CYAN}[0]{Colors.RESET} Bersihkan projek TIDAK AKTIF saja (> 30 hari tidak diedit)")
        print(f" {Colors.BRIGHT_MAGENTA}[s]{Colors.RESET} {Colors.BOLD}Bersihkan CACHE GLOBAL SISTEM (Temp, Update, Chrome, Edge, dll){Colors.RESET}")
        print(f" {Colors.BRIGHT_BLUE}[d]{Colors.RESET} {Colors.BOLD}Rapikan & Kelola folder DOWNLOADS (Kategori, Duplikat, Sampah){Colors.RESET}")
        print(f" {Colors.BRIGHT_CYAN}[w]{Colors.RESET} {Colors.BOLD}Scan SEMUA DRIVE Windows (Drive C: & D:){Colors.RESET}")
        print(f" {Colors.CYAN}[c]{Colors.RESET} Ganti direktori / drive target (cth: C:\\, D:\\, atau folder kustom)")
        print(f" {Colors.YELLOW}[t]{Colors.RESET} Ganti Mode Hapus (Saat ini: {trash_mode_text})")
        print(f" {Colors.CYAN}[l]{Colors.RESET} Lihat isi file log (.log)")
        print(f" {Colors.CYAN}[r]{Colors.RESET} Scan ulang direktori")
        print(f" {Colors.RED}[q]{Colors.RESET} Keluar")

        try:
            choice = input(f"\n{Colors.BOLD}Pilih nomor/aksi: {Colors.RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nKeluar.")
            break

        if choice in {"q", "exit"}:
            print("Keluar dari cleaner.")
            break
        elif choice == "d":
            from organize_downloads import run_interactive_menu as run_dl_menu
            run_dl_menu()
            continue
        elif choice == "s":
            handle_system_cache_menu(logger=logger, use_trash=use_trash)
            continue
        elif choice == "w":
            drives = get_available_drives()
            current_targets = drives
            print_success(f"Beralih memindai SEMUA Drive: {', '.join(str(d) for d in drives)}")
            continue
        elif choice == "t":
            use_trash = not use_trash
            continue
        elif choice == "r":
            continue
        elif choice == "l":
            print(f"\n{Colors.BOLD}=== Isi Terakhir {logger.log_path} ==={Colors.RESET}")
            print(logger.read_recent_lines(35))
            input(f"{Colors.DIM}Tekan Enter untuk kembali...{Colors.RESET}")
            continue
        elif choice == "c":
            avail = get_available_drives()
            drives_str = ", ".join(f"[{d.drive}]" for d in avail)
            new_path_str = input(f"Masukkan path folder / drive (Ditemukan: {drives_str}): ").strip()
            if new_path_str:
                p = Path(os.path.expanduser(new_path_str))
                if p.is_dir():
                    current_targets = [p]
                else:
                    print_error(f"Direktori '{new_path_str}' tidak valid.")
            continue

        selected_projs: List[Project] = []
        action_name = ""

        if choice == "1":
            selected_projs = active_projects
            action_name = "SEMUA projek"
        elif choice == "2":
            selected_projs = flutter_projs
            action_name = "projek FLUTTER"
        elif choice == "3":
            selected_projs = node_projs
            action_name = "projek NODE.JS"
        elif choice == "4":
            selected_projs = python_projs
            action_name = "cache PYTHON"
        elif choice == "5":
            selected_projs = php_projs
            action_name = "projek PHP / LARAVEL"
        elif choice == "6":
            selected_projs = gradle_projs
            action_name = "projek GRADLE / ANDROID"
        elif choice == "7":
            selected_projs = dotnet_projs
            action_name = "projek .NET / C#"
        elif choice == "8":
            selected_projs = golang_projs
            action_name = "projek GO / GOLANG"
        elif choice == "9":
            sel_str = input(f"Masukkan nomor projek (1-{len(active_projects)}, pisahkan koma/range): ").strip()
            indices = parse_index_selection(sel_str, len(active_projects))
            if not indices:
                print_warning("Tidak ada projek yang dipilih.")
                continue
            selected_projs = [active_projects[i] for i in indices]
            action_name = f"{len(selected_projs)} projek yang dipilih"
        elif choice == "0":
            selected_projs = [p for p in active_projects if p.days_since_modified >= 30]
            action_name = f"{len(selected_projs)} projek tidak aktif (> 30 hari)"
        else:
            print_error("Pilihan tidak valid.")
            continue

        if not selected_projs:
            print_warning(f"Tidak ada {action_name} yang memiliki cache/file pembersih.")
            continue

        calc_bytes = sum(p.total_cleanable_bytes for p in selected_projs)
        print(f"\n{Colors.BOLD}Detail yang akan dibersihkan ({action_name}):{Colors.RESET}")
        for p in selected_projs:
            drive_info = f"[{p.path.drive}] " if p.path.drive else ""
            print(f" • {Colors.CYAN}{drive_info}{p.name}{Colors.RESET} ({p.display_name}): {p.formatted_total_size}")
        print(f"Total ruang yang akan dihemat: {Colors.BRIGHT_GREEN}{Colors.BOLD}{format_size(calc_bytes)}{Colors.RESET}")

        target_action_desc = f"pindahkan ke {trash_name}" if use_trash else "HAPUS PERMANEN"
        if not confirm_action(f"Yakin ingin {target_action_desc} untuk {action_name}?"):
            print("Pembersihan dibatalkan.")
            continue

        print(f"\n{Colors.BOLD}Memulai proses pembersihan...{Colors.RESET}")
        results = execute_cleaning_batch(
            projects_to_clean=selected_projs,
            cleaners_map=cleaners_map,
            dry_run=False,
            use_trash=use_trash,
        )
        print_clean_results(results)

        # Log deleted items to .log file
        logged_path = logger.log_session(
            target_dir=current_targets[0],
            results_by_project=results,
            use_trash=use_trash,
            dry_run=False,
        )
        print_success(f"Catatan pembersihan telah disimpan ke: {Colors.BOLD}{logged_path}{Colors.RESET}")
        input(f"\n{Colors.DIM}Tekan Enter untuk kembali ke menu...{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Project Cleaner CLI - Bersihkan build/cache projek Flutter, Node.js, Python, PHP, Go, .NET, Gradle, dan System Caches di Windows & macOS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh Penggunaan:
  python cleaner.py                          # Mode interaktif
  python cleaner.py --scan                   # Analisa dan scan folder parent (dry-run)
  python cleaner.py C:\\ --scan               # Analisa seluruh Drive C:
  python cleaner.py D:\\ --scan               # Analisa seluruh Drive D:
  python cleaner.py --all-drives --scan      # Analisa SEMUA Drive Windows (C: & D:)
  python cleaner.py --drives C,D --scan      # Analisa drive C dan D bersamaan
  python cleaner.py --system-caches          # Bersihkan cache global sistem Windows (Temp, Chrome, Update, dll)
  python cleaner.py --php                    # Bersihkan projek PHP / Laravel saja
  python cleaner.py --go                     # Bersihkan projek Go / Golang saja
  python cleaner.py --dotnet                 # Bersihkan projek .NET / C# saja
  python cleaner.py --flutter                # Bersihkan projek Flutter saja
  python cleaner.py --node                   # Bersihkan node_modules & build Node.js
  python cleaner.py --python                 # Bersihkan __pycache__ & caches Python
  python cleaner.py --all -y                 # Bersihkan semua tanpa konfirmasi
  python cleaner.py --days 30                # Bersihkan projek yang tidak aktif > 30 hari
  python cleaner.py --trash                  # Pindahkan ke Windows Recycle Bin alih-alih hapus permanen
  python cleaner.py --log-file my.log        # Simpan riwayat ke file log khusus
        """,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path ke direktori yang ingin dibersihkan (default: direktori parent atau saat ini).",
    )
    parser.add_argument("-s", "--scan", "--dry-run", dest="dry_run", action="store_true", help="Hanya scan dan tampilkan ukuran tanpa menghapus.")
    parser.add_argument("--downloads", action="store_true", help="Buka pengatur dan pembersih folder Downloads.")
    parser.add_argument("--system-caches", action="store_true", help="Scan dan bersihkan cache global sistem Windows / macOS (Temp, Update, NPM, Gradle, dll).")
    parser.add_argument("--all-drives", action="store_true", help="Scan semua drive yang terdeteksi di sistem (misal Drive C: dan D:).")
    parser.add_argument("--drives", type=str, default="", help="Daftar drive yang ingin discan (pisahkan koma, contoh: C,D).")
    parser.add_argument("--flutter", action="store_true", help="Hanya bersihkan projek Flutter (flutter clean & build).")
    parser.add_argument("--node", action="store_true", help="Hanya bersihkan projek Node.js (node_modules, .next, dist).")
    parser.add_argument("--python", action="store_true", help="Hanya bersihkan cache Python (__pycache__, pytest, dll).")
    parser.add_argument("--php", action="store_true", help="Hanya bersihkan projek PHP / Laravel (storage/logs, views, vendor).")
    parser.add_argument("--go", "--golang", dest="golang", action="store_true", help="Hanya bersihkan projek Go / Golang (bin, dist, tmp).")
    parser.add_argument("--dotnet", "--csharp", dest="dotnet", action="store_true", help="Hanya bersihkan projek .NET / C# (bin, obj, .vs).")
    parser.add_argument("--rust", action="store_true", help="Hanya bersihkan projek Rust / Cargo (target).")
    parser.add_argument("--venv", action="store_true", help="Sertakan virtual environment Python (.venv, venv) untuk dihapus.")
    parser.add_argument("--gradle", action="store_true", help="Hanya bersihkan Gradle / Android (.gradle, build).")
    parser.add_argument("--ios", "--xcode", dest="xcode", action="store_true", help="Hanya bersihkan Xcode / iOS (Pods, DerivedData).")
    parser.add_argument("--all", action="store_true", help="Bersihkan semua jenis projek yang ditemukan.")
    parser.add_argument("--days", type=int, default=None, help="Hanya bersihkan projek yang tidak dimodifikasi dalam N hari.")
    parser.add_argument("--min-size", type=int, default=0, help="Hanya bersihkan item berukuran minimal N MB (contoh: --min-size 50).")
    parser.add_argument("-t", "--trash", action="store_true", help="Pindahkan file ke Recycle Bin / Trash alih-alih menghapus permanen.")
    parser.add_argument("-y", "--yes", "--force", dest="force", action="store_true", help="Lewati prompt konfirmasi (otomatis Ya).")
    parser.add_argument("--depth", type=int, default=4, help="Kedalaman pencarian folder (default: 4).")
    parser.add_argument("--exclude", type=str, default="", help="Daftar nama folder yang dikecualikan (pisahkan koma).")
    parser.add_argument("--log-file", type=str, default=None, help="Path ke file .log tujuan (default: cleaner.log di folder cleaner).")

    args = parser.parse_args()

    # Determine target directories
    target_dirs: List[Path] = []
    if args.all_drives:
        target_dirs = get_available_drives()
    elif args.drives:
        for d in args.drives.split(","):
            d = d.strip()
            if d:
                drive_p = Path(f"{d}:/") if len(d) == 1 else Path(d)
                if drive_p.exists():
                    target_dirs.append(drive_p)
                else:
                    print_warning(f"Drive atau path '{d}' tidak ditemukan, dilewati.")
    elif args.path:
        target_dirs = [Path(os.path.expanduser(args.path)).resolve()]
    else:
        current_dir = Path.cwd().resolve()
        parent_dir = current_dir.parent
        if current_dir.name == "cleaner" and parent_dir.exists():
            target_dirs = [parent_dir]
        else:
            target_dirs = [current_dir]

    if not target_dirs:
        print_error("Tidak ada direktori target valid yang dapat dipindai.")
        sys.exit(1)

    ignore_set = set()
    if args.exclude:
        ignore_set = {x.strip() for x in args.exclude.split(",") if x.strip()}

    custom_log_path = Path(os.path.expanduser(args.log_file)) if args.log_file else None
    logger = CleanerLogger(custom_log_path)

    # Handle --downloads via CLI
    if args.downloads:
        from organize_downloads import run_interactive_menu as run_dl_menu
        run_dl_menu()
        return

    # Handle --system-caches via CLI
    if args.system_caches:
        handle_system_cache_menu(logger=logger, use_trash=args.trash)
        return

    has_specific_action = (
        args.flutter
        or args.node
        or args.python
        or args.php
        or args.golang
        or args.dotnet
        or args.rust
        or args.gradle
        or args.xcode
        or args.all
        or args.all_drives
        or bool(args.drives)
        or args.days is not None
        or args.dry_run
    )

    # Interactive mode
    if not has_specific_action and not args.path:
        run_interactive_menu(
            target_paths=target_dirs,
            include_venv=args.venv,
            max_depth=args.depth,
            ignore_dirs=ignore_set,
            log_file=custom_log_path,
        )
        return

    # CLI automated mode
    cleaners_map = get_cleaners_dict()
    selected_cleaners = []

    if args.flutter and "flutter" in cleaners_map:
        selected_cleaners.append(cleaners_map["flutter"])
    if args.node and "node" in cleaners_map:
        selected_cleaners.append(cleaners_map["node"])
    if args.python and "python" in cleaners_map:
        selected_cleaners.append(cleaners_map["python"])
    if args.php and "php" in cleaners_map:
        selected_cleaners.append(cleaners_map["php"])
    if args.golang and "golang" in cleaners_map:
        selected_cleaners.append(cleaners_map["golang"])
    if args.dotnet and "dotnet" in cleaners_map:
        selected_cleaners.append(cleaners_map["dotnet"])
    if args.rust and "rust" in cleaners_map:
        selected_cleaners.append(cleaners_map["rust"])
    if args.gradle and "gradle" in cleaners_map:
        selected_cleaners.append(cleaners_map["gradle"])
    if args.xcode and "xcode" in cleaners_map:
        selected_cleaners.append(cleaners_map["xcode"])

    if args.all or not selected_cleaners:
        selected_cleaners = list(cleaners_map.values())

    print_banner()
    targets_desc = ", ".join(str(d) for d in target_dirs)
    print_info(f"Target Direktori : {Colors.BOLD}{targets_desc}{Colors.RESET}")
    print_info(f"Filter Cleaner   : {', '.join(c.display_name for c in selected_cleaners)}")
    print_info(f"File Catatan Log : {Colors.CYAN}{logger.log_path}{Colors.RESET}")
    if args.dry_run:
        print_info(f"Mode             : {Colors.BRIGHT_YELLOW}DRY-RUN / ANALISIS (Tidak menghapus data){Colors.RESET}")

    scanner = ProjectScanner(
        cleaners=selected_cleaners,
        ignore_dirs=ignore_set,
        max_depth=args.depth,
        include_optional=args.venv,
    )

    print(f"{Colors.DIM}Memindai berkas...{Colors.RESET}")
    if len(target_dirs) > 1:
        projects = scanner.scan_multiple(target_dirs)
        title = f"Hasil Scan di Semua Drive ({targets_desc})"
    else:
        projects = scanner.scan(target_dirs[0])
        title = f"Hasil Scan di {target_dirs[0]}"

    if args.days is not None:
        projects = [p for p in projects if p.days_since_modified >= args.days]

    display_project_table(projects, title=title)

    active_projects = [p for p in projects if p.total_cleanable_bytes > 0]
    if not active_projects:
        print_success("Tidak ada file yang perlu dibersihkan.")
        return

    if args.dry_run:
        print_info("Dry-run selesai. Jalankan tanpa flag --scan / --dry-run untuk melakukan pembersihan.")
        return

    total_bytes = sum(p.total_cleanable_bytes for p in active_projects)
    trash_name = "Recycle Bin" if platform.system() == "Windows" else "Trash"
    target_action_desc = f"pindahkan ke {trash_name}" if args.trash else "HAPUS PERMANEN"
    if not args.force:
        if not confirm_action(f"Yakin ingin {target_action_desc} data sebesar {format_size(total_bytes)}?"):
            print("Pembersihan dibatalkan.")
            return

    min_bytes = args.min_size * 1024 * 1024
    results = execute_cleaning_batch(
        projects_to_clean=active_projects,
        cleaners_map=cleaners_map,
        dry_run=False,
        use_trash=args.trash,
        min_size_bytes=min_bytes,
    )
    print_clean_results(results)

    logged_path = logger.log_session(
        target_dir=target_dirs[0],
        results_by_project=results,
        use_trash=args.trash,
        dry_run=False,
    )
    print_success(f"Daftar item yang dihapus telah disimpan ke file log: {Colors.BOLD}{logged_path}{Colors.RESET}")


if __name__ == "__main__":
    main()
