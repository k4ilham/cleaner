#!/usr/bin/env python3
"""
Inercorp Disk Usage & File Manager
Interactive File Explorer and Disk Space Analyzer for Windows & macOS.
Identifies large files taking up disk space with one-click safe Recycle Bin deletion.

Usage:
  python file_manager.py                 # Launch Modern GUI
  python file_manager.py "C:\\path"       # Launch GUI at specified path
  python file_manager.py --cli           # Launch Terminal CLI interactive browser
  python file_manager.py --cli --scan    # Run deep scan for largest files in terminal
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Inercorp Disk Usage & File Manager - Temukan file besar yang memakan ruang disk dan hapus dengan aman.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path folder yang ingin dijelajahi (default: C:\\inercorp\\download atau user home)",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Jalankan di mode terminal / CLI (tanpa jendela GUI)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Langsung jalankan Deep Scan untuk mencari file-file terbesar di subfolder (mode CLI)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Jumlah file terbesar yang ditampilkan pada mode scan (default: 50)",
    )
    parser.add_argument(
        "--min-size",
        default="10MB",
        help="Batas ukuran minimum file untuk scan (contoh: 50MB, 100MB, 1GB; default: 10MB)",
    )

    args = parser.parse_args()

    # Determine target initial directory
    target_path = Path(args.path) if args.path else None
    if not target_path or not target_path.exists():
        proj_dl = Path("C:/project/download")
        inercorp_dl = Path("C:/inercorp/download")
        if proj_dl.exists():
            target_path = proj_dl
        elif inercorp_dl.exists():
            target_path = inercorp_dl
        else:
            target_path = Path.home()

    # CLI Mode
    if args.cli:
        from src.file_manager_cli import run_cli_explorer, run_cli_deep_scan
        if args.scan:
            run_cli_deep_scan(target_path, min_size_str=args.min_size, max_count=args.top)
        else:
            run_cli_explorer(target_path)
        return

    # GUI Mode (Default)
    try:
        from src.file_manager_gui import launch_gui
        launch_gui(str(target_path))
    except Exception as e:
        print(f"Peringatan: Gagal meluncurkan GUI ({e}). Beralih otomatis ke mode terminal CLI...")
        from src.file_manager_cli import run_cli_explorer
        run_cli_explorer(target_path)


if __name__ == "__main__":
    main()

