"""
Terminal / CLI interface for File Manager & Disk Usage Analyzer.
Uses 'rich' library to render beautiful terminal tables and interactive menus.
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from src.file_manager_core import (
    format_bytes,
    get_drive_info,
    get_folder_fast_items,
    calculate_folder_size,
    scan_largest_files,
    delete_multiple,
    reveal_in_explorer,
    parse_size_str,
)

console = Console()


def print_drive_banner(path: str):
    """Print drive storage usage banner."""
    info = get_drive_info(path)
    crit_tag = "[bold red]⚠️  KRITIS (< 10% SISA)![/]" if info["is_critical"] else ""
    
    panel_text = (
        f"[bold cyan]Drive {path[:3]}[/]  |  "
        f"Kapasitas: [bold]{info['total_str']}[/]  |  "
        f"Terpakai: [bold yellow]{info['used_str']}[/] ({info['percent']:.1f}%)  |  "
        f"Sisa Ruang Bebas: [bold green]{info['free_str']}[/]  {crit_tag}"
    )
    console.print(Panel(panel_text, title="[bold]Informasi Kapasitas Disk[/]", border_style="blue"))


def run_cli_explorer(folder_path: Path):
    """Interactive CLI folder browser."""
    current = folder_path.resolve()
    
    while True:
        console.clear()
        print_drive_banner(str(current))
        console.print(f"[bold yellow]Lokasi Saat Ini:[/] [underline]{current}[/]\n")

        items = get_folder_fast_items(current)
        
        # Sort by size descending
        items.sort(key=lambda x: x["size"], reverse=True)

        table = Table(title=f"Isi Folder ({len(items)} Item) - Diurutkan dari Ukuran Terbesar", show_lines=False)
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Tipe", width=6, justify="center")
        table.add_column("Nama Berkas / Folder", style="bold white", width=45)
        table.add_column("Ukuran", justify="right", style="cyan", width=12)
        table.add_column("Kategori", style="green", width=18)
        table.add_column("Terakhir Diubah", style="dim", width=20)

        for idx, it in enumerate(items[:50], start=1):
            t_icon = "📁 Dir" if it["is_dir"] else "📄 File"
            table.add_row(
                str(idx),
                t_icon,
                it["name"][:43] + ("..." if len(it["name"]) > 43 else ""),
                it["size_str"],
                it.get("category", "-"),
                it.get("mtime", "-"),
            )

        console.print(table)
        if len(items) > 50:
            console.print(f"[dim](Menampilkan 50 item teratas dari total {len(items)} item)[/]")

        console.print("\n[bold cyan]Perintah:[/]")
        console.print("  [bold green][Nomor][/] : Masuk ke folder atau lihat detail file")
        console.print("  [bold green]..[/]      : Naik ke folder induk (parent directory)")
        console.print("  [bold green]top[/]     : Pindai subfolder untuk mencari file TERBESAR (Deep Scan)")
        console.print("  [bold green]del [N][/] : Hapus item nomor N (contoh: del 3 atau del 1,2,5)")
        console.print("  [bold green]open[/]    : Buka folder ini di Windows File Explorer")
        console.print("  [bold green]q[/]       : Keluar")

        cmd = Prompt.ask("\n[bold yellow]Pilihan Anda[/]").strip()

        if cmd.lower() in ("q", "quit", "exit"):
            break
        elif cmd == "..":
            if current.parent and current.parent != current:
                current = current.parent
        elif cmd.lower() == "open":
            reveal_in_explorer(current)
        elif cmd.lower() == "top":
            run_cli_deep_scan(current)
        elif cmd.lower().startswith("del "):
            parts = cmd[4:].strip().split(",")
            selected_items = []
            for p in parts:
                p = p.strip()
                if p.isdigit():
                    num = int(p)
                    if 1 <= num <= len(items):
                        selected_items.append(items[num - 1])
            
            if selected_items:
                _confirm_and_delete_cli(selected_items)
            else:
                console.print("[red]Nomor item tidak valid.[/]")
                Prompt.ask("Tekan Enter untuk lanjut...")
        elif cmd.isdigit():
            num = int(cmd)
            if 1 <= num <= len(items):
                target = items[num - 1]
                if target["is_dir"]:
                    current = Path(target["path"])
                else:
                    console.print(f"\n[bold]Detail File:[/] {target['name']}")
                    console.print(f"Path: {target['path']}")
                    console.print(f"Ukuran: {target['size_str']}")
                    action = Prompt.ask("Aksi: [o] Buka di Explorer, [d] Hapus, [b] Kembali", choices=["o", "d", "b"], default="b")
                    if action == "o":
                        reveal_in_explorer(Path(target["path"]))
                    elif action == "d":
                        _confirm_and_delete_cli([target])
        else:
            p = Path(cmd)
            if p.exists() and p.is_dir():
                current = p.resolve()


def run_cli_deep_scan(root_path: Path, min_size_str: str = "10MB", max_count: int = 50):
    """Deep scan CLI view for largest files across subfolders."""
    min_bytes = parse_size_str(min_size_str)
    
    console.print(f"\n[bold cyan]Memindai file terbesar di {root_path} (Min: {min_size_str}, Max: {max_count})...[/]")
    
    with console.status("[bold green]Sedang memindai subfolder...[/]", spinner="dots"):
        results = scan_largest_files(root_path, min_size_bytes=min_bytes, max_results=max_count)

    if not results:
        console.print("[yellow]Tidak ditemukan file yang melebihi batas ukuran tersebut.[/]")
        Prompt.ask("Tekan Enter untuk kembali...")
        return

    table = Table(title=f"Top {len(results)} File Terbesar di Subfolder", show_lines=False)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Nama File", style="bold white", width=35)
    table.add_column("Ukuran", justify="right", style="bold red", width=12)
    table.add_column("Kategori", style="green", width=15)
    table.add_column("Subfolder", style="cyan", width=40)

    for idx, r in enumerate(results, start=1):
        rel_folder = os.path.relpath(r["folder"], root_path)
        table.add_row(
            str(idx),
            r["name"][:33] + ("..." if len(r["name"]) > 33 else ""),
            r["size_str"],
            r["category"],
            rel_folder[:38] + ("..." if len(rel_folder) > 38 else ""),
        )

    console.print(table)

    total_sz = sum(r["size"] for r in results)
    console.print(f"\n[bold]Total kapasitas top {len(results)} file:[/] [bold red]{format_bytes(total_sz)}[/]")

    console.print("\n[bold cyan]Aksi:[/]")
    console.print("  [bold green]del [N][/] : Hapus file nomor N (contoh: del 1 atau del 1,2,3)")
    console.print("  [bold green]open [N][/]: Buka file nomor N di File Explorer")
    console.print("  [bold green]b[/]       : Kembali ke penjelajah folder")

    while True:
        subcmd = Prompt.ask("\n[bold yellow]Pilihan Anda[/]").strip()
        if subcmd.lower() in ("b", "back", "q"):
            break
        elif subcmd.lower().startswith("open "):
            num_str = subcmd[5:].strip()
            if num_str.isdigit():
                n = int(num_str)
                if 1 <= n <= len(results):
                    reveal_in_explorer(Path(results[n - 1]["path"]))
        elif subcmd.lower().startswith("del "):
            parts = subcmd[4:].strip().split(",")
            selected = []
            for p in parts:
                p = p.strip()
                if p.isdigit():
                    n = int(p)
                    if 1 <= n <= len(results):
                        selected.append(results[n - 1])
            if selected:
                _confirm_and_delete_cli(selected)
                break


def _confirm_and_delete_cli(items: list[dict]):
    """Confirmation and deletion handler for CLI."""
    total_bytes = sum(it.get("size", 0) for it in items)
    console.print(f"\n[bold red]⚠️  Peringatan Penghapusan[/]")
    console.print(f"Jumlah item: [bold]{len(items)}[/]")
    console.print(f"Kapasitas yang akan dibebaskan: [bold red]{format_bytes(total_bytes)}[/]")
    
    for it in items[:10]:
        console.print(f" - {it['name']} ({format_bytes(it.get('size', 0))})")
    if len(items) > 10:
        console.print(f" ... dan {len(items) - 10} item lainnya.")

    mode = Prompt.ask(
        "\nPilih metode penghapusan",
        choices=["recycle", "permanent", "batal"],
        default="recycle",
    )

    if mode == "batal":
        console.print("[yellow]Penghapusan dibatalkan.[/]")
        Prompt.ask("Tekan Enter untuk lanjut...")
        return

    use_trash = (mode == "recycle")
    paths = [Path(it["path"]) for it in items]

    res = delete_multiple(paths, use_recycle_bin=use_trash)
    
    dest_str = "Recycle Bin" if use_trash else "Permanen"
    console.print(f"[bold green]✓ Berhasil menghapus {res['success_count']} item ke {dest_str}![/]")
    console.print(f"[bold green]Ruang disk yang dibebaskan: {res['freed_str']}[/]")

    if res["failed_count"] > 0:
        console.print(f"[bold red]⚠️  {res['failed_count']} item gagal dihapus.[/]")

    Prompt.ask("\nTekan Enter untuk lanjut...")
