"""
Modern File Manager & Disk Usage Space Analyzer GUI
Built with CustomTkinter & ttk.Treeview.
Features fast directory browsing, background directory sizing,
deep scan for top largest files, and safe Recycle Bin / permanent deletion.
"""

import os
import platform
import queue
import threading
from datetime import datetime
from pathlib import Path
from tkinter import Menu, messagebox, ttk
import customtkinter as ctk

from src.file_manager_core import (
    calculate_folder_size,
    delete_multiple,
    format_bytes,
    get_available_drives,
    get_drive_info,
    get_folder_fast_items,
    open_default_app,
    parse_size_str,
    reveal_in_explorer,
    scan_largest_files,
)


class ConfirmDeleteDialog(ctk.CTkToplevel):
    """Modern modal dialog confirming deletion of files with Recycle Bin / Permanent option."""

    def __init__(self, parent, items_to_delete: list[dict]):
        super().__init__(parent)
        self.result = None  # None = Cancel, 'recycle' = Trash, 'permanent' = Permanent
        self.items = items_to_delete

        self.title("Konfirmasi Penghapusan Berkas")
        self.geometry("540x480")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        total_bytes = sum(item.get("size", 0) for item in self.items)
        count = len(self.items)

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="⚠️ Konfirmasi Hapus File / Folder",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f87171"
        )
        title_lbl.pack(anchor="w")

        info_lbl = ctk.CTkLabel(
            header_frame,
            text=f"Anda akan menghapus {count} item.\nKapasitas disk yang akan dibebaskan: {format_bytes(total_bytes)}",
            font=ctk.CTkFont(size=13),
            justify="left"
        )
        info_lbl.pack(anchor="w", pady=(6, 0))

        # Items list scrollable
        list_frame = ctk.CTkScrollableFrame(self, height=180, fg_color=("#e2e8f0", "#1e293b"))
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for it in self.items[:100]:
            name = it.get("name", "Unknown")
            sz = format_bytes(it.get("size", 0))
            row = ctk.CTkFrame(list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            n_lbl = ctk.CTkLabel(row, text=name, anchor="w", font=ctk.CTkFont(size=11))
            n_lbl.pack(side="left", fill="x", expand=True)
            s_lbl = ctk.CTkLabel(row, text=sz, font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
            s_lbl.pack(side="right")

        if count > 100:
            extra_lbl = ctk.CTkLabel(list_frame, text=f"... dan {count - 100} item lainnya", font=ctk.CTkFont(size=11, slant="italic"))
            extra_lbl.pack(pady=4)

        # Mode selection
        self.delete_mode_var = ctk.StringVar(value="recycle")

        mode_frame = ctk.CTkFrame(self, fg_color=("#f1f5f9", "#0f172a"), corner_radius=8)
        mode_frame.pack(fill="x", padx=20, pady=10)

        rb1 = ctk.CTkRadioButton(
            mode_frame,
            text="Pindahkan ke Windows Recycle Bin (Aman & Bisa Di-Restore)",
            variable=self.delete_mode_var,
            value="recycle",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3b82f6"
        )
        rb1.pack(anchor="w", padx=15, pady=(12, 6))

        rb2 = ctk.CTkRadioButton(
            mode_frame,
            text="Hapus Permanen (Langsung Kosongkan Disk, Tidak Bisa Di-Restore)",
            variable=self.delete_mode_var,
            value="permanent",
            font=ctk.CTkFont(size=12),
            text_color="#f87171",
            fg_color="#ef4444"
        )
        rb2.pack(anchor="w", padx=15, pady=(0, 12))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Batal",
            width=100,
            fg_color=("#94a3b8", "#475569"),
            hover_color=("#64748b", "#334155"),
            command=self._on_cancel
        )
        cancel_btn.pack(side="left")

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Hapus Sekarang",
            width=150,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._on_confirm
        )
        confirm_btn.pack(side="right")

    def _on_confirm(self):
        self.result = self.delete_mode_var.get()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class FileManagerApp(ctk.CTk):
    """Main Application Window."""

    def __init__(self, initial_path: str = None):
        super().__init__()

        # Window configuration
        self.title("Inercorp Disk Usage & File Manager")
        self.geometry("1200x760")
        self.minsize(980, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initial directory path
        if initial_path and Path(initial_path).exists():
            self.current_path = Path(initial_path).resolve()
        else:
            proj_dl = Path("C:/project/download")
            inercorp_dl = Path("C:/inercorp/download")
            if proj_dl.exists():
                self.current_path = proj_dl
            elif inercorp_dl.exists():
                self.current_path = inercorp_dl
            else:
                self.current_path = Path.home()

        # State tracking
        self.current_items = []
        self.filtered_items = []
        self.folder_sizes_thread = None
        self.cancel_folder_sizes = False
        self.deep_scan_thread = None
        self.cancel_deep_scan = False
        self.sort_column = "size"
        self.sort_reverse = True
        self.event_queue = queue.Queue()

        # Build UI layout
        self._setup_styles()
        self._build_top_drive_banner()
        self._build_navigation_bar()
        self._build_quick_shortcuts_bar()
        self._build_main_tabview()
        self._build_status_bar()

        # Setup context menus & key bindings
        self._setup_context_menus()
        self._setup_keybindings()

        # Start periodic main-thread event queue polling
        self._poll_event_queue()

        # Initial load
        self.navigate_to(self.current_path)

    def _poll_event_queue(self):
        """Poll thread-safe event queue on main Tk thread."""
        try:
            while True:
                event_type, data = self.event_queue.get_nowait()
                if event_type == "folder_size_updated":
                    self._on_subfolder_size_calculated()
                elif event_type == "deep_scan_progress":
                    scanned, found, current_dir = data
                    self.scanner_status_lbl.configure(
                        text=f"Memindai subfolder... Telah dicek {scanned:,} file | Ditemukan {found} file besar | Sedang memeriksa: {current_dir}"
                    )
                elif event_type == "deep_scan_done":
                    self._on_deep_scan_done(data)
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            self.after(50, self._poll_event_queue)

    def _setup_styles(self):
        """Configure ttk Treeview styles to integrate smoothly with Dark theme."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Treeview styling
        self.style.configure(
            "Custom.Treeview",
            background="#1e293b",
            foreground="#f8fafc",
            fieldbackground="#1e293b",
            rowheight=30,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background="#0f172a",
            foreground="#94a3b8",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(8, 6),
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", "#2563eb")],
            foreground=[("selected", "#ffffff")],
        )
        self.style.map(
            "Custom.Treeview.Heading",
            background=[("active", "#1e293b")],
            foreground=[("active", "#38bdf8")],
        )

    def _build_top_drive_banner(self):
        """Build disk capacity overview card with progress bar and critical alert."""
        self.drive_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("#f8fafc", "#0f172a"))
        self.drive_frame.pack(fill="x", padx=16, pady=(12, 6))

        top_row = ctk.CTkFrame(self.drive_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(10, 4))

        # Drive selector
        drives = get_available_drives()
        self.drive_var = ctk.StringVar(value=drives[0] if drives else "C:\\")

        drive_icon = ctk.CTkLabel(top_row, text="💾 Drive:", font=ctk.CTkFont(size=13, weight="bold"))
        drive_icon.pack(side="left", padx=(0, 6))

        self.drive_menu = ctk.CTkOptionMenu(
            top_row,
            values=drives,
            variable=self.drive_var,
            width=90,
            command=self._on_drive_changed,
        )
        self.drive_menu.pack(side="left", padx=(0, 15))

        # Disk stats label
        self.disk_stats_lbl = ctk.CTkLabel(
            top_row,
            text="Memuat status drive...",
            font=ctk.CTkFont(size=12),
        )
        self.disk_stats_lbl.pack(side="left")

        # Warning badge
        self.warning_badge = ctk.CTkLabel(
            top_row,
            text="⚠️ DISK KRITIS (< 10% SISA)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ef4444",
            fg_color=("#fee2e2", "#450a0a"),
            corner_radius=6,
            padx=10,
            pady=2,
        )

        # Progress bar
        self.disk_progress = ctk.CTkProgressBar(self.drive_frame, height=10, corner_radius=5)
        self.disk_progress.pack(fill="x", padx=14, pady=(0, 10))

        self.update_drive_banner()

    def update_drive_banner(self):
        """Update drive statistics display."""
        drive = self.drive_var.get()
        info = get_drive_info(drive)

        pct = info["percent"]
        used_s = info["used_str"]
        tot_s = info["total_str"]
        free_s = info["free_str"]

        self.disk_stats_lbl.configure(
            text=f"Terpakai: {used_s} / {tot_s} ({pct:.1f}%)   |   Tersisa: {free_s}"
        )
        self.disk_progress.set(pct / 100.0)

        if info["is_critical"]:
            self.disk_progress.configure(progress_color="#ef4444")
            self.warning_badge.pack(side="right")
        elif info["is_warning"]:
            self.disk_progress.configure(progress_color="#f59e0b")
            self.warning_badge.pack_forget()
        else:
            self.disk_progress.configure(progress_color="#10b981")
            self.warning_badge.pack_forget()

    def _on_drive_changed(self, choice):
        self.navigate_to(Path(choice))

    def _build_navigation_bar(self):
        """Build breadcrumbs/address bar and navigation controls."""
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=16, pady=4)

        # Up (Back) button
        up_btn = ctk.CTkButton(
            nav_frame,
            text="⬆️ Naik",
            width=80,
            command=self._go_parent_directory,
        )
        up_btn.pack(side="left", padx=(0, 8))

        # Address bar
        self.path_entry_var = ctk.StringVar(value=str(self.current_path))
        self.path_entry = ctk.CTkEntry(
            nav_frame,
            textvariable=self.path_entry_var,
            font=ctk.CTkFont(size=12),
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.bind("<Return>", lambda e: self._on_address_entered())

        # Browse button
        browse_btn = ctk.CTkButton(
            nav_frame,
            text="📂 Browse...",
            width=90,
            fg_color=("#64748b", "#334155"),
            hover_color=("#475569", "#1e293b"),
            command=self._pick_folder,
        )
        browse_btn.pack(side="left", padx=(0, 8))

        # Refresh button
        refresh_btn = ctk.CTkButton(
            nav_frame,
            text="🔄 Refresh",
            width=85,
            command=self.refresh,
        )
        refresh_btn.pack(side="left")

    def _build_quick_shortcuts_bar(self):
        """Quick jump shortcut chips."""
        shortcuts_frame = ctk.CTkFrame(self, fg_color="transparent")
        shortcuts_frame.pack(fill="x", padx=16, pady=(2, 6))

        lbl = ctk.CTkLabel(shortcuts_frame, text="Pintasan Cepat:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8")
        lbl.pack(side="left", padx=(0, 8))

        dl_target = Path("C:/Maulana/10_Documents_Downloads/download") if Path("C:/Maulana/10_Documents_Downloads/download").exists() else Path("C:/project/download")
        doc_target = Path("C:/Maulana/10_Documents_Downloads/Document") if Path("C:/Maulana/10_Documents_Downloads/Document").exists() else Path("C:/project/Document")

        shortcuts = [
            ("📁 Maulana Root", Path("C:/Maulana")),
            ("📥 Download", dl_target),
            ("📄 Document", doc_target),
            ("💼 Inercorp", Path("C:/Maulana/01_Inercorp_Projects")),
            ("🌐 Web Backend", Path("C:/Maulana/05_Web_Backend_PHP")),
            ("⬇️ Downloads User", Path.home() / "Downloads"),
            ("📁 Documents User", Path.home() / "Documents"),
            ("💾 Drive C:", Path("C:/")),
        ]

        for title, p in shortcuts:
            btn = ctk.CTkButton(
                shortcuts_frame,
                text=title,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color=("#e2e8f0", "#1e293b"),
                text_color=("#0f172a", "#f1f5f9"),
                hover_color=("#cbd5e1", "#334155"),
                command=lambda target=p: self.navigate_to(target),
            )
            btn.pack(side="left", padx=3)

    def _build_main_tabview(self):
        """Build tabview containing Folder Explorer and Deep Large Files Scanner."""
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        self.tab_explorer = self.tabview.add("📁 Penjelajah Folder & Ukuran")
        self.tab_scanner = self.tabview.add("🚀 Deep Scan: Temukan File Terbesar")

        self._build_folder_explorer_tab()
        self._build_deep_scanner_tab()

    def _build_folder_explorer_tab(self):
        """Folder Explorer with search filter, treeview table, and size breakdown."""
        filter_bar = ctk.CTkFrame(self.tab_explorer, fg_color="transparent")
        filter_bar.pack(fill="x", padx=4, pady=(4, 8))

        # Search box
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._apply_search_filter())

        search_icon = ctk.CTkLabel(filter_bar, text="🔍 Filter:", font=ctk.CTkFont(size=12))
        search_icon.pack(side="left", padx=(4, 6))

        self.search_entry = ctk.CTkEntry(
            filter_bar,
            textvariable=self.search_var,
            placeholder_text="Ketik nama atau ekstensi file (misal .zip, .mp4, tesis)...",
            width=360,
        )
        self.search_entry.pack(side="left", padx=(0, 12))

        # Quick sorting hints
        hint_lbl = ctk.CTkLabel(
            filter_bar,
            text="Tip: Klik judul kolom untuk mengurutkan. Default diurutkan dari ukuran file terbesar.",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#94a3b8",
        )
        hint_lbl.pack(side="left")

        # Table container
        table_frame = ctk.CTkFrame(self.tab_explorer, corner_radius=8, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=4, pady=4)

        columns = ("type", "name", "size_str", "pct_str", "category", "items_count", "mtime")
        self.tree_explorer = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            style="Custom.Treeview",
        )

        # Headings
        self.tree_explorer.heading("type", text="Tipe", command=lambda: self._sort_explorer_by("is_dir"))
        self.tree_explorer.heading("name", text="Nama Berkas / Folder", command=lambda: self._sort_explorer_by("name"))
        self.tree_explorer.heading("size_str", text="Ukuran", command=lambda: self._sort_explorer_by("size"))
        self.tree_explorer.heading("pct_str", text="% Folder", command=lambda: self._sort_explorer_by("size"))
        self.tree_explorer.heading("category", text="Kategori", command=lambda: self._sort_explorer_by("category"))
        self.tree_explorer.heading("items_count", text="Item", command=lambda: self._sort_explorer_by("items_count"))
        self.tree_explorer.heading("mtime", text="Waktu Modifikasi", command=lambda: self._sort_explorer_by("mtime"))

        # Column widths
        self.tree_explorer.column("type", width=55, anchor="center")
        self.tree_explorer.column("name", width=380, anchor="w")
        self.tree_explorer.column("size_str", width=110, anchor="e")
        self.tree_explorer.column("pct_str", width=80, anchor="e")
        self.tree_explorer.column("category", width=120, anchor="w")
        self.tree_explorer.column("items_count", width=70, anchor="center")
        self.tree_explorer.column("mtime", width=150, anchor="w")

        # Scrollbar
        scroll_y = ctk.CTkScrollbar(table_frame, command=self.tree_explorer.yview)
        self.tree_explorer.configure(yscrollcommand=scroll_y.set)

        self.tree_explorer.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        # Events
        self.tree_explorer.bind("<Double-1>", self._on_explorer_double_click)
        self.tree_explorer.bind("<<TreeviewSelect>>", self._on_explorer_selection_changed)

    def _build_deep_scanner_tab(self):
        """Deep Scanner tab for finding top large files across subfolders."""
        controls_frame = ctk.CTkFrame(self.tab_scanner, fg_color="transparent")
        controls_frame.pack(fill="x", padx=4, pady=(6, 10))

        # Size threshold dropdown
        sz_lbl = ctk.CTkLabel(controls_frame, text="Ukuran Min:", font=ctk.CTkFont(size=12))
        sz_lbl.pack(side="left", padx=(4, 6))

        self.min_size_var = ctk.StringVar(value="> 10 MB")
        min_sizes = ["> 1 MB", "> 10 MB", "> 50 MB", "> 100 MB", "> 500 MB", "> 1 GB", "Semua Ukuran (> 0 B)"]
        self.min_size_menu = ctk.CTkOptionMenu(controls_frame, values=min_sizes, variable=self.min_size_var, width=130)
        self.min_size_menu.pack(side="left", padx=(0, 16))

        # Max results dropdown
        max_lbl = ctk.CTkLabel(controls_frame, text="Batas Hasil:", font=ctk.CTkFont(size=12))
        max_lbl.pack(side="left", padx=(0, 6))

        self.max_results_var = ctk.StringVar(value="Top 50 File")
        max_options = ["Top 20 File", "Top 50 File", "Top 100 File", "Top 250 File", "Semua"]
        self.max_results_menu = ctk.CTkOptionMenu(controls_frame, values=max_options, variable=self.max_results_var, width=120)
        self.max_results_menu.pack(side="left", padx=(0, 16))

        # Scan button
        self.scan_btn = ctk.CTkButton(
            controls_frame,
            text="🔍 Mulai Pindai Subfolder",
            width=180,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._start_deep_scan,
        )
        self.scan_btn.pack(side="left", padx=(0, 8))

        # Stop button
        self.stop_scan_btn = ctk.CTkButton(
            controls_frame,
            text="⏹️ Stop",
            width=70,
            fg_color=("#94a3b8", "#475569"),
            state="disabled",
            command=self._stop_deep_scan,
        )
        self.stop_scan_btn.pack(side="left")

        # Scanner status banner
        self.scanner_status_frame = ctk.CTkFrame(self.tab_scanner, corner_radius=6, fg_color=("#f1f5f9", "#0f172a"))
        self.scanner_status_frame.pack(fill="x", padx=4, pady=(0, 8))

        self.scanner_status_lbl = ctk.CTkLabel(
            self.scanner_status_frame,
            text="Pilih kriteria ukuran dan klik 'Mulai Pindai Subfolder' untuk mencari file-file berukuran besar di folder saat ini dan seluruh cabangnya.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        self.scanner_status_lbl.pack(anchor="w", padx=12, pady=6)

        # Scanner Treeview Table
        scan_table_frame = ctk.CTkFrame(self.tab_scanner, corner_radius=8, fg_color="transparent")
        scan_table_frame.pack(fill="both", expand=True, padx=4, pady=4)

        scan_columns = ("name", "size_str", "category", "folder", "mtime")
        self.tree_scanner = ttk.Treeview(
            scan_table_frame,
            columns=scan_columns,
            show="headings",
            selectmode="extended",
            style="Custom.Treeview",
        )

        self.tree_scanner.heading("name", text="Nama File")
        self.tree_scanner.heading("size_str", text="Ukuran File")
        self.tree_scanner.heading("category", text="Kategori")
        self.tree_scanner.heading("folder", text="Lokasi Subfolder")
        self.tree_scanner.heading("mtime", text="Waktu Terakhir Diubah")

        self.tree_scanner.column("name", width=320, anchor="w")
        self.tree_scanner.column("size_str", width=120, anchor="e")
        self.tree_scanner.column("category", width=130, anchor="w")
        self.tree_scanner.column("folder", width=420, anchor="w")
        self.tree_scanner.column("mtime", width=150, anchor="w")

        scroll_scan_y = ctk.CTkScrollbar(scan_table_frame, command=self.tree_scanner.yview)
        self.tree_scanner.configure(yscrollcommand=scroll_scan_y.set)

        self.tree_scanner.pack(side="left", fill="both", expand=True)
        scroll_scan_y.pack(side="right", fill="y")

        self.tree_scanner.bind("<Double-1>", self._on_scanner_double_click)
        self.tree_scanner.bind("<<TreeviewSelect>>", self._on_scanner_selection_changed)

        self.deep_scan_items = []

    def _build_status_bar(self):
        """Action bar with status label and Delete / Explorer action buttons."""
        self.action_frame = ctk.CTkFrame(self, fg_color=("#f8fafc", "#0f172a"), corner_radius=10)
        self.action_frame.pack(fill="x", padx=16, pady=(0, 12))

        # Status text
        self.status_lbl = ctk.CTkLabel(
            self.action_frame,
            text="Siap.",
            font=ctk.CTkFont(size=12),
        )
        self.status_lbl.pack(side="left", padx=16, pady=10)

        # Action Buttons
        del_btn = ctk.CTkButton(
            self.action_frame,
            text="🗑️ Hapus Terpilih...",
            width=140,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._delete_selected_items,
        )
        del_btn.pack(side="right", padx=(6, 16), pady=8)

        reveal_btn = ctk.CTkButton(
            self.action_frame,
            text="📂 Buka di Explorer",
            width=140,
            fg_color=("#64748b", "#334155"),
            hover_color=("#475569", "#1e293b"),
            command=self._reveal_selected_in_explorer,
        )
        reveal_btn.pack(side="right", padx=(6, 6), pady=8)

    def _setup_context_menus(self):
        """Create right-click menus for tables."""
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Buka / Jalankan", command=self._open_selected_item)
        self.context_menu.add_command(label="Buka di File Explorer", command=self._reveal_selected_in_explorer)
        self.context_menu.add_command(label="Salin Path Lengkap", command=self._copy_selected_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Hapus (Pilihan Aman / Permanen)...", command=self._delete_selected_items)

        def show_ctx_explorer(event):
            item = self.tree_explorer.identify_row(event.y)
            if item:
                if item not in self.tree_explorer.selection():
                    self.tree_explorer.selection_set(item)
                self.context_menu.tk_popup(event.x_root, event.y_root)

        def show_ctx_scanner(event):
            item = self.tree_scanner.identify_row(event.y)
            if item:
                if item not in self.tree_scanner.selection():
                    self.tree_scanner.selection_set(item)
                self.context_menu.tk_popup(event.x_root, event.y_root)

        self.tree_explorer.bind("<Button-3>", show_ctx_explorer)
        self.tree_scanner.bind("<Button-3>", show_ctx_scanner)

    def _setup_keybindings(self):
        """Configure keyboard shortcuts."""
        self.bind("<F5>", lambda e: self.refresh())
        self.bind("<BackSpace>", lambda e: self._go_parent_directory() if not isinstance(self.focus_get(), ctk.CTkEntry) else None)
        self.bind("<Delete>", lambda e: self._delete_selected_items() if not isinstance(self.focus_get(), ctk.CTkEntry) else None)

    # ----------------------------------------------------
    # Navigation & Folder Explorer Logic
    # ----------------------------------------------------

    def navigate_to(self, path: Path):
        """Navigate to a target directory."""
        if not path.exists():
            messagebox.showerror("Error", f"Folder tidak ditemukan:\n{path}")
            return

        if not path.is_dir():
            path = path.parent

        self.current_path = path.resolve()
        self.path_entry_var.set(str(self.current_path))

        # Check drive match
        drive_root = f"{self.current_path.drive}\\"
        if drive_root and drive_root != self.drive_var.get() and drive_root in get_available_drives():
            self.drive_var.set(drive_root)

        self.update_drive_banner()

        # Cancel any ongoing folder size background thread
        self.cancel_folder_sizes = True

        # Perform fast scan of immediate children
        self.current_items = get_folder_fast_items(self.current_path)

        # Clear search filter and populate
        self.search_var.set("")
        self._apply_search_filter()

        # Launch background thread to calculate directory sizes
        self._start_folder_sizes_worker()

    def refresh(self):
        """Refresh current view and disk stats."""
        self.navigate_to(self.current_path)

    def _go_parent_directory(self):
        """Navigate up to parent directory."""
        parent = self.current_path.parent
        if parent and parent != self.current_path:
            self.navigate_to(parent)

    def _pick_folder(self):
        """Folder picker dialog."""
        selected = ctk.filedialog.askdirectory(initialdir=str(self.current_path), title="Pilih Folder")
        if selected:
            self.navigate_to(Path(selected))

    def _on_address_entered(self):
        """Handle Enter key in address bar."""
        typed_path = Path(self.path_entry_var.get().strip())
        self.navigate_to(typed_path)

    def _apply_search_filter(self):
        """Filter table items by search query."""
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_items = list(self.current_items)
        else:
            self.filtered_items = [
                it for it in self.current_items
                if query in it["name"].lower() or query in it.get("category", "").lower() or query in it.get("extension", "").lower()
            ]

        self._sort_and_display_explorer()

    def _sort_explorer_by(self, col: str):
        """Toggle sort column and order."""
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = True if col in ("size", "mtime", "items_count") else False

        self._sort_and_display_explorer()

    def _sort_and_display_explorer(self):
        """Sort filtered items and populate the Treeview."""
        # Folders can either be grouped on top or sorted alongside files
        # Users analyzing disk usage usually want the absolute largest item (file or folder) at the top!
        def sort_key(it):
            val = it.get(self.sort_column, 0)
            if self.sort_column == "is_dir":
                return 1 if it["is_dir"] else 0
            if isinstance(val, str):
                return val.lower()
            return val

        self.filtered_items.sort(key=sort_key, reverse=self.sort_reverse)

        # Calculate total size of current folder items for % calculation
        total_folder_size = sum(it.get("size", 0) for it in self.current_items)

        # Clear tree
        self.tree_explorer.delete(*self.tree_explorer.get_children())

        for idx, it in enumerate(self.filtered_items):
            type_icon = "📁" if it["is_dir"] else "📄"
            pct_val = (it.get("size", 0) / total_folder_size * 100) if total_folder_size > 0 else 0
            pct_str = f"{pct_val:.1f}%" if it.get("size", 0) > 0 else "-"

            values = (
                type_icon,
                it["name"],
                it.get("size_str", "0 B"),
                pct_str,
                it.get("category", "-"),
                str(it.get("items_count", "-")),
                it.get("mtime", "-"),
            )
            # Store item index as treeview iid
            self.tree_explorer.insert("", "end", iid=str(idx), values=values)

        self._update_explorer_status_label()

    def _start_folder_sizes_worker(self):
        """Worker thread calculating subfolder sizes in background."""
        self.cancel_folder_sizes = False
        target_path = self.current_path

        def worker():
            for item in self.current_items:
                if self.cancel_folder_sizes or self.current_path != target_path:
                    break
                if item["is_dir"]:
                    folder_p = Path(item["path"])
                    sz, count = calculate_folder_size(
                        folder_p,
                        cancel_check=lambda: self.cancel_folder_sizes or (self.current_path != target_path)
                    )
                    if self.cancel_folder_sizes or self.current_path != target_path:
                        break
                    item["size"] = sz
                    item["size_str"] = format_bytes(sz)
                    item["items_count"] = f"{count} file"

                    # Schedule UI update via thread-safe queue
                    self.event_queue.put(("folder_size_updated", None))

        self.folder_sizes_thread = threading.Thread(target=worker, daemon=True)
        self.folder_sizes_thread.start()

    def _on_subfolder_size_calculated(self):
        """Called when a subfolder size is calculated to refresh display."""
        if not self.cancel_folder_sizes:
            self._sort_and_display_explorer()

    def _on_explorer_double_click(self, event):
        """Double click enters directory or opens file."""
        selected_iid = self.tree_explorer.focus()
        if not selected_iid:
            return
        idx = int(selected_iid)
        if idx < len(self.filtered_items):
            item = self.filtered_items[idx]
            target = Path(item["path"])
            if item["is_dir"]:
                self.navigate_to(target)
            else:
                open_default_app(target)

    def _on_explorer_selection_changed(self, event):
        self._update_explorer_status_label()

    def _update_explorer_status_label(self):
        selected_iids = self.tree_explorer.selection()
        total_items = len(self.filtered_items)

        if not selected_iids:
            total_sz = sum(it.get("size", 0) for it in self.filtered_items)
            self.status_lbl.configure(
                text=f"Total: {total_items} item di folder ini   |   Total kapasitas: {format_bytes(total_sz)}"
            )
        else:
            sel_items = [self.filtered_items[int(i)] for i in selected_iids if int(i) < len(self.filtered_items)]
            sel_sz = sum(it.get("size", 0) for it in sel_items)
            self.status_lbl.configure(
                text=f"Terpilih: {len(sel_items)} item   |   Ukuran gabungan: {format_bytes(sel_sz)}"
            )

    # ----------------------------------------------------
    # Deep Scanner Logic (Space Hogs Finder)
    # ----------------------------------------------------

    def _start_deep_scan(self):
        """Initiate deep recursive scan for large files."""
        if self.deep_scan_thread and self.deep_scan_thread.is_alive():
            return

        min_map = {
            "> 1 MB": 1 * 1024 * 1024,
            "> 10 MB": 10 * 1024 * 1024,
            "> 50 MB": 50 * 1024 * 1024,
            "> 100 MB": 100 * 1024 * 1024,
            "> 500 MB": 500 * 1024 * 1024,
            "> 1 GB": 1024 * 1024 * 1024,
            "Semua Ukuran (> 0 B)": 0,
        }
        min_bytes = min_map.get(self.min_size_var.get(), 10 * 1024 * 1024)

        max_map = {
            "Top 20 File": 20,
            "Top 50 File": 50,
            "Top 100 File": 100,
            "Top 250 File": 250,
            "Semua": 0,
        }
        max_res = max_map.get(self.max_results_var.get(), 50)

        self.cancel_deep_scan = False
        self.scan_btn.configure(state="disabled")
        self.stop_scan_btn.configure(state="normal")
        self.tree_scanner.delete(*self.tree_scanner.get_children())
        self.deep_scan_items = []

        root_to_scan = self.current_path

        def progress_cb(scanned, found, current_dir):
            self.event_queue.put(("deep_scan_progress", (scanned, found, current_dir)))

        def worker():
            results = scan_largest_files(
                root_path=root_to_scan,
                min_size_bytes=min_bytes,
                max_results=max_res,
                progress_callback=progress_cb,
                cancel_check=lambda: self.cancel_deep_scan,
            )
            self.event_queue.put(("deep_scan_done", results))

        self.deep_scan_thread = threading.Thread(target=worker, daemon=True)
        self.deep_scan_thread.start()

    def _on_deep_scan_done(self, results):
        """Called on main thread when deep scan finishes."""
        self.deep_scan_items = results
        self.scan_btn.configure(state="normal")
        self.stop_scan_btn.configure(state="disabled")

        for idx, r in enumerate(results):
            values = (
                r["name"],
                r["size_str"],
                r["category"],
                r["folder"],
                r["mtime"],
            )
            self.tree_scanner.insert("", "end", iid=str(idx), values=values)

        total_sz = sum(r["size"] for r in results)
        status_txt = "Selesai!" if not self.cancel_deep_scan else "Pemindaian dihentikan pengguna."
        self.scanner_status_lbl.configure(
            text=f"{status_txt} Ditemukan {len(results)} file terbesar (Total kapasitas: {format_bytes(total_sz)})."
        )

        self.deep_scan_thread = threading.Thread(target=worker, daemon=True)
        self.deep_scan_thread.start()

    def _stop_deep_scan(self):
        """Signal deep scan thread to stop."""
        self.cancel_deep_scan = True
        self.stop_scan_btn.configure(state="disabled")

    def _on_scanner_double_click(self, event):
        selected_iid = self.tree_scanner.focus()
        if not selected_iid:
            return
        idx = int(selected_iid)
        if idx < len(self.deep_scan_items):
            target = Path(self.deep_scan_items[idx]["path"])
            open_default_app(target)

    def _on_scanner_selection_changed(self, event):
        selected_iids = self.tree_scanner.selection()
        if not selected_iids:
            return
        sel_items = [self.deep_scan_items[int(i)] for i in selected_iids if int(i) < len(self.deep_scan_items)]
        sel_sz = sum(it.get("size", 0) for it in sel_items)
        self.status_lbl.configure(
            text=f"Terpilih di hasil Scan: {len(sel_items)} file   |   Total kapasitas: {format_bytes(sel_sz)}"
        )

    # ----------------------------------------------------
    # Actions: Delete, Reveal, Open, Copy
    # ----------------------------------------------------

    def _get_active_selection(self) -> list[dict]:
        """Get selected item dicts from whichever tab is currently active."""
        current_tab = self.tabview.get()
        if current_tab == "📁 Penjelajah Folder & Ukuran":
            selected_iids = self.tree_explorer.selection()
            return [self.filtered_items[int(i)] for i in selected_iids if int(i) < len(self.filtered_items)]
        else:
            selected_iids = self.tree_scanner.selection()
            return [self.deep_scan_items[int(i)] for i in selected_iids if int(i) < len(self.deep_scan_items)]

    def _delete_selected_items(self):
        """Confirm and delete selected items from active tab."""
        items = self._get_active_selection()
        if not items:
            messagebox.showinfo("Informasi", "Pilih setidaknya satu file atau folder yang ingin dihapus.")
            return

        # Show modern confirmation modal
        dialog = ConfirmDeleteDialog(self, items)
        self.wait_window(dialog)

        if not dialog.result:
            return  # Cancelled

        use_recycle_bin = (dialog.result == "recycle")
        paths = [Path(it["path"]) for it in items]

        # Execute deletion
        res = delete_multiple(paths, use_recycle_bin=use_recycle_bin)

        mode_str = "Windows Recycle Bin" if use_recycle_bin else "Permanen"
        msg = f"Berhasil menghapus {res['success_count']} item ke {mode_str}.\nRuang disk yang dibebaskan: {res['freed_str']}."

        if res["failed_count"] > 0:
            msg += f"\n\n⚠️ {res['failed_count']} item gagal dihapus (mungkin sedang digunakan proses lain)."

        messagebox.showinfo("Hasil Penghapusan", msg)

        # Refresh views
        self.refresh()
        if self.tabview.get() != "📁 Penjelajah Folder & Ukuran" and self.deep_scan_items:
            # Re-filter deep scanner list
            existing_iids = self.tree_scanner.get_children()
            for iid in existing_iids:
                idx = int(iid)
                if idx < len(self.deep_scan_items):
                    p = Path(self.deep_scan_items[idx]["path"])
                    if not p.exists():
                        self.tree_scanner.delete(iid)

    def _reveal_selected_in_explorer(self):
        """Open selected file or folder in Windows Explorer."""
        items = self._get_active_selection()
        if not items:
            reveal_in_explorer(self.current_path)
            return

        for it in items:
            reveal_in_explorer(Path(it["path"]))
            break  # Reveal the first selected

    def _open_selected_item(self):
        """Open selected item with default app."""
        items = self._get_active_selection()
        if not items:
            return
        it = items[0]
        p = Path(it["path"])
        if it.get("is_dir"):
            self.navigate_to(p)
        else:
            open_default_app(p)

    def _copy_selected_path(self):
        """Copy path of selected items to clipboard."""
        items = self._get_active_selection()
        if not items:
            return
        paths_str = "\n".join(it["path"] for it in items)
        self.clipboard_clear()
        self.clipboard_append(paths_str)
        self.status_lbl.configure(text=f"Path telah disalin ke clipboard ({len(items)} item).")


def launch_gui(initial_path: str = None):
    """Launch the application mainloop."""
    app = FileManagerApp(initial_path=initial_path)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
