#!/usr/bin/env python3
"""
Project Cleaner - CLI and Interactive Tool to clean developer projects and system caches.
Supports Flutter, Node.js, Python, Gradle/Android, Xcode/iOS, Rust, and System/Developer caches.
Logs all deleted files and freed space to a .log file.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

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
    target_action_desc = "pindahkan ke macOS Trash" if use_trash else "HAPUS PERMANEN"
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
    root_path: Path,
    include_venv: bool = False,
    max_depth: int = 4,
    ignore_dirs: Optional[Set[str]] = None,
    log_file: Optional[Path] = None,
):
    """Run full interactive terminal interface."""
    cleaners_map = get_cleaners_dict()
    use_trash = False
    logger = CleanerLogger(log_file)

    while True:
        print_banner()
        print_info(f"Target Direktori : {Colors.BOLD}{root_path.resolve()}{Colors.RESET}")
        trash_mode_text = (
            f"{Colors.BRIGHT_MAGENTA}macOS Trash (Tempat Sampah){Colors.RESET}"
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

        projects = scanner.scan(root_path)
        active_projects = [p for p in projects if p.total_cleanable_bytes > 0]

        display_project_table(projects, title=f"Projek Ditemukan di {root_path.name}")

        total_bytes = sum(p.total_cleanable_bytes for p in active_projects)
        flutter_projs = [p for p in active_projects if p.project_type == "flutter"]
        node_projs = [p for p in active_projects if p.project_type == "node"]
        python_projs = [p for p in active_projects if p.project_type == "python"]
        gradle_projs = [p for p in active_projects if p.project_type == "gradle"]
        xcode_projs = [p for p in active_projects if p.project_type == "xcode"]

        flutter_size = format_size(sum(p.total_cleanable_bytes for p in flutter_projs))
        node_size = format_size(sum(p.total_cleanable_bytes for p in node_projs))
        python_size = format_size(sum(p.total_cleanable_bytes for p in python_projs))
        gradle_size = format_size(sum(p.total_cleanable_bytes for p in gradle_projs))
        xcode_size = format_size(sum(p.total_cleanable_bytes for p in xcode_projs))

        print(f"{Colors.BOLD}{Colors.BRIGHT_WHITE}PILIHAN TINDAKAN:{Colors.RESET}")
        print(f" {Colors.CYAN}[1]{Colors.RESET} Bersihkan SEMUA projek ({Colors.BRIGHT_GREEN}{format_size(total_bytes)}{Colors.RESET})")
        print(f" {Colors.CYAN}[2]{Colors.RESET} Bersihkan projek FLUTTER saja ({len(flutter_projs)} projek, {Colors.BRIGHT_GREEN}{flutter_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[3]{Colors.RESET} Bersihkan projek NODE.JS saja ({len(node_projs)} projek, {Colors.BRIGHT_GREEN}{node_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[4]{Colors.RESET} Bersihkan cache PYTHON saja ({len(python_projs)} projek, {Colors.BRIGHT_GREEN}{python_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[5]{Colors.RESET} Bersihkan projek GRADLE / ANDROID ({len(gradle_projs)} projek, {Colors.BRIGHT_GREEN}{gradle_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[6]{Colors.RESET} Bersihkan projek XCODE / IOS ({len(xcode_projs)} projek, {Colors.BRIGHT_GREEN}{xcode_size}{Colors.RESET})")
        print(f" {Colors.CYAN}[7]{Colors.RESET} Pilih projek tertentu berdasarkan nomor (cth: 1, 3, 5-8)")
        print(f" {Colors.CYAN}[8]{Colors.RESET} Bersihkan projek TIDAK AKTIF saja (> 30 hari tidak diedit)")
        print(f" {Colors.BRIGHT_MAGENTA}[s]{Colors.RESET} {Colors.BOLD}Bersihkan CACHE GLOBAL SISTEM & DEVELOPER (~24 GB: NPM, Gradle, Chrome, dll){Colors.RESET}")
        print(f" {Colors.BRIGHT_BLUE}[d]{Colors.RESET} {Colors.BOLD}Rapikan & Kelola folder DOWNLOADS (Kategori, Duplikat, Hapus Sampah){Colors.RESET}")
        print(f" {Colors.YELLOW}[t]{Colors.RESET} Ganti Mode Hapus (Saat ini: {trash_mode_text})")
        print(f" {Colors.CYAN}[l]{Colors.RESET} Lihat isi file log (.log)")
        print(f" {Colors.CYAN}[r]{Colors.RESET} Scan ulang direktori")
        print(f" {Colors.CYAN}[c]{Colors.RESET} Ubah direktori target")
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
            new_path_str = input("Masukkan path folder yang ingin di-scan: ").strip()
            if new_path_str:
                p = Path(os.path.expanduser(new_path_str))
                if p.is_dir():
                    root_path = p
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
            selected_projs = gradle_projs
            action_name = "projek GRADLE / ANDROID"
        elif choice == "6":
            selected_projs = xcode_projs
            action_name = "projek XCODE / IOS"
        elif choice == "7":
            sel_str = input(f"Masukkan nomor projek (1-{len(active_projects)}, pisahkan koma/range): ").strip()
            indices = parse_index_selection(sel_str, len(active_projects))
            if not indices:
                print_warning("Tidak ada projek yang dipilih.")
                continue
            selected_projs = [active_projects[i] for i in indices]
            action_name = f"{len(selected_projs)} projek yang dipilih"
        elif choice == "8":
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
            print(f" • {Colors.CYAN}{p.name}{Colors.RESET} ({p.display_name}): {p.formatted_total_size}")
        print(f"Total ruang yang akan dihemat: {Colors.BRIGHT_GREEN}{Colors.BOLD}{format_size(calc_bytes)}{Colors.RESET}")

        target_action_desc = "pindahkan ke macOS Trash" if use_trash else "HAPUS PERMANEN"
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
            target_dir=root_path,
            results_by_project=results,
            use_trash=use_trash,
            dry_run=False,
        )
        print_success(f"Daftar item yang dihapus telah disimpan ke file log: {Colors.BOLD}{logged_path}{Colors.RESET}")

        input(f"\n{Colors.DIM}Tekan Enter untuk kembali ke menu...{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Project Cleaner CLI - Bersihkan build/cache projek Flutter, Node.js, Python, Gradle, iOS, dan System Caches.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh Penggunaan:
  python3 cleaner.py                        # Mode interaktif
  python3 cleaner.py ~/Documents/projek     # Mode interaktif pada folder tertentu
  python3 cleaner.py --scan                 # Analisa dan tampilkan ukuran (dry-run)
  python3 cleaner.py --system-caches        # Bersihkan cache sistem & developer global
  python3 cleaner.py --flutter              # Bersihkan projek Flutter saja
  python3 cleaner.py --node                 # Bersihkan node_modules & build Node.js
  python3 cleaner.py --python               # Bersihkan __pycache__ & caches Python
  python3 cleaner.py --all -y               # Bersihkan semua tanpa konfirmasi
  python3 cleaner.py --days 30              # Bersihkan projek yang tidak aktif > 30 hari
  python3 cleaner.py --trash                # Pindahkan ke macOS Trash alih-alih hapus permanen
  python3 cleaner.py --log-file my.log      # Simpan riwayat ke file log khusus
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
    parser.add_argument("--system-caches", action="store_true", help="Scan dan bersihkan cache global sistem & developer (NPM, Gradle, Xcode, Chrome, dll).")
    parser.add_argument("--flutter", action="store_true", help="Hanya bersihkan projek Flutter (flutter clean & build).")
    parser.add_argument("--node", action="store_true", help="Hanya bersihkan projek Node.js (node_modules, .next, dist).")
    parser.add_argument("--python", action="store_true", help="Hanya bersihkan cache Python (__pycache__, pytest, dll).")
    parser.add_argument("--venv", action="store_true", help="Sertakan virtual environment Python (.venv, venv) untuk dihapus.")
    parser.add_argument("--gradle", action="store_true", help="Hanya bersihkan Gradle / Android (.gradle, build).")
    parser.add_argument("--ios", "--xcode", dest="xcode", action="store_true", help="Hanya bersihkan Xcode / iOS (Pods, DerivedData).")
    parser.add_argument("--all", action="store_true", help="Bersihkan semua jenis projek yang ditemukan.")
    parser.add_argument("--days", type=int, default=None, help="Hanya bersihkan projek yang tidak dimodifikasi dalam N hari.")
    parser.add_argument("--min-size", type=int, default=0, help="Hanya bersihkan item berukuran minimal N MB (contoh: --min-size 50).")
    parser.add_argument("-t", "--trash", action="store_true", help="Pindahkan file ke macOS Trash alih-alih menghapus permanen.")
    parser.add_argument("-y", "--yes", "--force", dest="force", action="store_true", help="Lewati prompt konfirmasi (otomatis Ya).")
    parser.add_argument("--depth", type=int, default=4, help="Kedalaman pencarian folder (default: 4).")
    parser.add_argument("--exclude", type=str, default="", help="Daftar nama folder yang dikecualikan (pisahkan koma).")
    parser.add_argument("--log-file", type=str, default=None, help="Path ke file .log tujuan (default: cleaner.log di folder cleaner).")

    args = parser.parse_args()

    # Determine default path:
    target_dir: Path
    if args.path:
        target_dir = Path(os.path.expanduser(args.path)).resolve()
    else:
        current_dir = Path.cwd().resolve()
        parent_dir = current_dir.parent
        if current_dir.name == "cleaner" and parent_dir.exists():
            target_dir = parent_dir
        else:
            target_dir = current_dir

    if not target_dir.exists() or not target_dir.is_dir():
        print_error(f"Direktori '{target_dir}' tidak ditemukan atau bukan folder.")
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
        or args.gradle
        or args.xcode
        or args.all
        or args.days is not None
        or args.dry_run
    )

    # Interactive mode
    if not has_specific_action:
        run_interactive_menu(
            root_path=target_dir,
            include_venv=args.venv,
            max_depth=args.depth,
            ignore_dirs=ignore_set,
            log_file=custom_log_path,
        )
        return

    # CLI automated mode
    cleaners_map = get_cleaners_dict()
    selected_cleaners = []

    if args.flutter:
        selected_cleaners.append(cleaners_map["flutter"])
    if args.node:
        selected_cleaners.append(cleaners_map["node"])
    if args.python:
        selected_cleaners.append(cleaners_map["python"])
    if args.gradle:
        selected_cleaners.append(cleaners_map["gradle"])
    if args.xcode:
        selected_cleaners.append(cleaners_map["xcode"])

    if args.all or not selected_cleaners:
        selected_cleaners = list(cleaners_map.values())

    print_banner()
    print_info(f"Target Direktori : {Colors.BOLD}{target_dir}{Colors.RESET}")
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
    projects = scanner.scan(target_dir)

    if args.days is not None:
        projects = [p for p in projects if p.days_since_modified >= args.days]

    display_project_table(projects, title=f"Hasil Scan di {target_dir.name}")

    active_projects = [p for p in projects if p.total_cleanable_bytes > 0]
    if not active_projects:
        print_success("Tidak ada file yang perlu dibersihkan.")
        return

    if args.dry_run:
        print_info("Dry-run selesai. Jalankan tanpa flag --scan / --dry-run untuk melakukan pembersihan.")
        return

    total_bytes = sum(p.total_cleanable_bytes for p in active_projects)
    target_action_desc = "pindahkan ke macOS Trash" if args.trash else "HAPUS PERMANEN"
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
        target_dir=target_dir,
        results_by_project=results,
        use_trash=args.trash,
        dry_run=False,
    )
    print_success(f"Daftar item yang dihapus telah disimpan ke file log: {Colors.BOLD}{logged_path}{Colors.RESET}")


if __name__ == "__main__":
    main()
