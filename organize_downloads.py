#!/usr/bin/env python3
"""
Downloads Folder Organizer & Cleaner CLI.
Rapikan dan bersihkan file unduhan ke dalam kategori otomatis dengan fitur UNDO.
"""

import argparse
import os
import sys
from pathlib import Path

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

from src.downloads_organizer import DownloadsOrganizer
from src.logger import CleanerLogger
from src.models import format_size
from src.trash import delete_target
from src.ui import (
    Colors,
    confirm_action,
    print_banner,
    print_error,
    print_info,
    print_success,
    print_warning,
)


def print_downloads_preview(organizer: DownloadsOrganizer):
    """Display categorized breakdown of files in Downloads."""
    grouped = organizer.scan_downloads()
    total_files = sum(len(fls) for fls in grouped.values())
    total_bytes = sum(sum(f.stat().st_size for f in fls) for fls in grouped.values())

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_WHITE}📂 Isi Folder Downloads Saat Ini:{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")

    if total_files == 0:
        print_info("Folder Downloads Anda sudah rapi dan bersih!")
        print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}\n")
        return grouped

    for cat, files in grouped.items():
        if files:
            cat_size = sum(f.stat().st_size for f in files)
            badge_color = Colors.BRIGHT_CYAN if cat != "Junk" else Colors.BRIGHT_RED
            print(f" {badge_color}📁 {cat:<18}{Colors.RESET} : {Colors.BOLD}{len(files):>2} file{Colors.RESET} ({format_size(cat_size)})")
            for f in files[:4]:
                print(f"    {Colors.DIM}• {f.name} ({format_size(f.stat().st_size)}){Colors.RESET}")
            if len(files) > 4:
                print(f"    {Colors.DIM}... dan {len(files) - 4} file lainnya{Colors.RESET}")

    print(f"{Colors.DIM}{'─' * 70}{Colors.RESET}")
    print(f" Total: {Colors.BOLD}{total_files} file{Colors.RESET} ({Colors.BRIGHT_GREEN}{format_size(total_bytes)}{Colors.RESET})\n")
    return grouped


def run_interactive_menu():
    organizer = DownloadsOrganizer()
    logger = CleanerLogger()

    while True:
        print_banner()
        print_info(f"Target Direktori : {Colors.BOLD}{organizer.downloads_dir}{Colors.RESET}")
        grouped = print_downloads_preview(organizer)

        total_files = sum(len(fls) for cat, fls in grouped.items() if cat != "Junk")
        junk_files = grouped.get("Junk", [])

        print(f"{Colors.BOLD}{Colors.BRIGHT_WHITE}PILIHAN TINDAKAN:{Colors.RESET}")
        print(f" {Colors.CYAN}[1]{Colors.RESET} Rapikan SEMUA file ke folder kategori (Documents, Images, Code, dll)")
        print(f" {Colors.CYAN}[2]{Colors.RESET} Bersihkan file sampah download (.crdownload, .part) - {len(junk_files)} file")
        print(f" {Colors.CYAN}[3]{Colors.RESET} Cari & hapus file duplikat")
        print(f" {Colors.CYAN}[4]{Colors.RESET} Pindahkan file installer besar (.dmg, .pkg) ke Tempat Sampah")
        print(f" {Colors.BRIGHT_YELLOW}[u]{Colors.RESET} UNDO perapian terakhir (Kembalikan file ke folder Downloads root)")
        print(f" {Colors.CYAN}[d]{Colors.RESET} Preview perpindahan file saja (Simulasi / Dry-Run)")
        print(f" {Colors.RED}[q]{Colors.RESET} Keluar")

        try:
            choice = input(f"\n{Colors.BOLD}Pilihan Anda: {Colors.RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nKeluar.")
            break

        if choice in {"q", "exit"}:
            print("Keluar dari Downloads Organizer.")
            break

        elif choice == "1":
            if total_files == 0:
                print_warning("Tidak ada file baru di folder Downloads yang perlu dirapikan.")
                input(f"{Colors.DIM}Tekan Enter...{Colors.RESET}")
                continue

            if not confirm_action(f"Yakin ingin memindahkan {total_files} file ke folder kategori?"):
                print("Dibatalkan.")
                continue

            moves = organizer.organize(dry_run=False)
            print_success(f"Berhasil merapikan {len(moves)} file ke folder kategori masing-masing!")
            print_info("Tips: Jika Anda ingin membatalkan, tekan [u] di menu untuk UNDO.")
            input(f"{Colors.DIM}Tekan Enter untuk lanjut...{Colors.RESET}")

        elif choice == "2":
            if not junk_files:
                print_info("Tidak ada file sampah (.crdownload / .part) ditemukan.")
                input(f"{Colors.DIM}Tekan Enter...{Colors.RESET}")
                continue

            cleaned = organizer.clean_junk(dry_run=False, use_trash=True)
            print_success(f"Berhasil memindahkan {len(cleaned)} file sampah ke Tempat Sampah (Trash).")
            input(f"{Colors.DIM}Tekan Enter untuk lanjut...{Colors.RESET}")

        elif choice == "3":
            print_info("Memindai file duplikat berdasarkan hash...")
            dups = organizer.find_duplicate_files()
            if not dups:
                print_success("Tidak ada file duplikat yang ditemukan!")
            else:
                total_dup_size = sum(s for _, _, s in dups)
                print(f"\nDitemukan {len(dups)} file duplikat ({format_size(total_dup_size)}):")
                for orig, dup, s in dups:
                    print(f" • {dup.name} (kembar dengan {orig.name}) - {format_size(s)}")
                if confirm_action("Pindahkan file duplikat ke Tempat Sampah?"):
                    for _, dup, _ in dups:
                        delete_target(dup, use_trash=True)
                    print_success(f"Berhasil memindahkan {len(dups)} file duplikat ke Trash.")
            input(f"{Colors.DIM}Tekan Enter untuk lanjut...{Colors.RESET}")

        elif choice == "4":
            installers = grouped.get("Installers", [])
            if not installers:
                print_info("Tidak ada file installer (.dmg, .pkg) di folder Downloads root.")
            else:
                total_inst_size = sum(f.stat().st_size for f in installers)
                print(f"\nInstaller ditemukan ({format_size(total_inst_size)}):")
                for f in installers:
                    print(f" • {f.name} ({format_size(f.stat().st_size)})")
                if confirm_action(f"Pindahkan {len(installers)} installer ke Tempat Sampah?"):
                    for f in installers:
                        delete_target(f, use_trash=True)
                    print_success(f"Berhasil memindahkan {len(installers)} installer ke Tempat Sampah.")
            input(f"{Colors.DIM}Tekan Enter untuk lanjut...{Colors.RESET}")

        elif choice == "u":
            restored, errors = organizer.undo_last_organization()
            if restored > 0:
                print_success(f"Berhasil mengembalikan {restored} file ke folder Downloads root!")
            if errors:
                for err in errors:
                    print_warning(err)
            input(f"{Colors.DIM}Tekan Enter untuk lanjut...{Colors.RESET}")

        elif choice == "d":
            moves = organizer.organize(dry_run=True)
            print(f"\n{Colors.BOLD}=== SIMULASI PERPINDAHAN FILE (DRY-RUN) ==={Colors.RESET}")
            for m in moves:
                cat_name = Path(m.current_path).parent.name
                print(f" • {m.filename} ➔ {Colors.CYAN}{cat_name}/{Colors.RESET} ({format_size(m.size_bytes)})")
            input(f"\n{Colors.DIM}Tekan Enter untuk kembali...{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Downloads Organizer - Rapikan folder Downloads ke dalam subfolder kategori otomatis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-s", "--scan", "--dry-run", dest="dry_run", action="store_true", help="Hanya preview pemindahan file tanpa memindahkan.")
    parser.add_argument("-a", "--auto", action="store_true", help="Langsung rapikan semua file ke folder kategori tanpa tanya.")
    parser.add_argument("--clean-junk", action="store_true", help="Hapus file unduhan rusak (.crdownload, .part).")
    parser.add_argument("-u", "--undo", action="store_true", help="Kembalikan file dari kategori ke folder Downloads root.")

    args = parser.parse_args()
    organizer = DownloadsOrganizer()

    if args.undo:
        restored, errors = organizer.undo_last_organization()
        if restored > 0:
            print_success(f"Berhasil mengembalikan {restored} file ke Downloads root.")
        for err in errors:
            print_warning(err)
        return

    if args.clean_junk:
        cleaned = organizer.clean_junk(dry_run=args.dry_run, use_trash=True)
        print_success(f"Berhasil membersihkan {len(cleaned)} file sampah.")
        return

    if args.auto:
        moves = organizer.organize(dry_run=False)
        print_success(f"Berhasil merapikan {len(moves)} file ke folder kategori.")
        return

    if args.dry_run:
        moves = organizer.organize(dry_run=True)
        print(f"\n{Colors.BOLD}=== SIMULASI PERPINDAHAN (DRY-RUN) ==={Colors.RESET}")
        for m in moves:
            cat_name = Path(m.current_path).parent.name
            print(f" • {m.filename} ➔ {cat_name}/ ({format_size(m.size_bytes)})")
        return

    # Default to interactive
    run_interactive_menu()


if __name__ == "__main__":
    main()
