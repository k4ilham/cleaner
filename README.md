# 🚀 Developer Project Cleaner & Downloads Organizer

Aplikasi Python modern, cepat, dan aman untuk memindai serta membersihkan berkas cache, build artifacts, `node_modules`, cache sistem developer, serta **merapikan folder Downloads** di Mac Anda.

Mendukung otomatisasi:
- **Flutter / Dart**: Menjalankan `flutter clean`, membersihkan `build/`, `.dart_tool/`, `.flutter-plugins`, build cache Android/iOS.
- **Node.js / Web**: Menghapus `node_modules/`, `.next/`, `.nuxt/`, `dist/`, `.output/`, `.turbo/`, `.cache/`, dll.
- **Python**: Menghapus `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, build & egg-info (dan opsional `.venv`).
- **Android / Gradle**: Menghapus `.gradle/`, `build/`, `app/build/`.
- **Xcode / iOS / macOS**: Menghapus `Pods/`, `DerivedData/`, `.build/`.
- **Rust / Cargo**: Menjalankan `cargo clean`, menghapus `target/`.
- **System & Developer Global Caches**: Membersihkan cache global `~/.npm` (5.8 GB), `~/.gradle/caches` (5.3 GB), Xcode DerivedData (1.1 GB), Chrome Cache (4.2 GB), Telegram Cache (880 MB), dll.
- **Downloads Folder Organizer & Cleaner**: Merapikan file unduhan ke dalam folder kategori otomatis (`Documents`, `Images`, `Spreadsheets`, `Code`, `Installers`, `Archives`, dll), mendeteksi file duplikat, membersihkan file unduhan rusak (`.crdownload`, `.part`), serta dilengkapi fitur **UNDO** untuk mengembalikan file ke posisi semula!
- **Pencatatan Log (`.log`)**: Semua berkas & folder yang dihapus otomatis dicatat rapi ke dalam file `.log`.

---

## 🌟 Fitur Utama

1. **Zero External Dependencies**: Berjalan langsung menggunakan bawaan Python 3 tanpa perlu `pip install`.
2. **Perapian Folder Downloads dengan Fitur UNDO**: Mengelompokkan file secara cerdas berdasarkan tipe ekstensi dan bisa dibatalkan (*revert*) kapan saja dengan 1 klik.
3. **Pencatatan Riwayat (`.log`) Otomatis**: Setiap item yang dihapus dicatat lengkap dengan timestamp, path lengkap, ukuran, dan modenya ke `cleaner.log`.
4. **Pembersih Cache Global Sistem (System Data)**: Mampu mendeteksi dan membersihkan puluhan gigabyte cache developer & aplikasi yang tersimpan di `~/Library` dan folder `~/.`.
5. **Terminal UI Interaktif**: Tabel ringkas dengan warna ANSI, menampilkan ukuran disk yang dapat dihemat per projek dan total GB.
6. **Safety First**:
   - **Mode Dry-Run (`--scan`)**: Analisa dan lihat kapasitas disk tanpa menghapus apapun.
   - **Dukungan macOS Trash (`--trash`)**: Pindahkan folder ke Tempat Sampah (*macOS Bin*) alih-alih dihapus permanen agar aman jika ingin di-*restore*.
   - **Filter Umur Projek (`--days 30`)**: Hanya bersihkan projek yang sudah tidak aktif / tidak diedit dalam X hari.

---

## ⚡ Cara Menjalankan

### 1. Merapikan Folder Downloads
Anda bisa menjalankan program pengatur Downloads langsung:
```bash
python3 /Users/mbairm12020/Documents/projek/cleaner/organize_downloads.py
```
Menu interaktif menyediakan:
* `[1]` Rapikan SEMUA file ke folder kategori (`Images/`, `Documents/`, `Code/`, dll)
* `[2]` Bersihkan file unduhan rusak / sementara (`.crdownload`, `.part`)
* `[3]` Cari & bersihkan file duplikat (identik)
* `[4]` Pindahkan installer aplikasi lama (`.dmg`, `.pkg`) ke Tempat Sampah
* `[u]` **UNDO**: Kembalikan semua file yang telah dirapikan ke folder Downloads semula
* `[d]` **Dry-run**: Simulasi perpindahan tanpa mengubah file

Atau perintah cepat:
```bash
# Preview simulasi perpindahan
python3 organize_downloads.py --dry-run

# Langsung rapikan otomatis
python3 organize_downloads.py --auto

# Batalkan perapian terakhir (UNDO)
python3 organize_downloads.py --undo
```

---

### 2. Menu Utama Project Cleaner
Jalankan di terminal:
```bash
python3 /Users/mbairm12020/Documents/projek/cleaner/cleaner.py
```
Menu interaktif menyediakan:
```text
PILIHAN TINDAKAN:
 [1] Bersihkan SEMUA projek yang ditemukan
 [2] Bersihkan projek FLUTTER saja (flutter clean & build cache)
 [3] Bersihkan projek NODE.JS saja (node_modules, .next, dist)
 [4] Bersihkan cache PYTHON saja (__pycache__, caches)
 [5] Bersihkan projek GRADLE / ANDROID (.gradle, build)
 [6] Bersihkan projek XCODE / IOS (Pods, DerivedData)
 [7] Pilih projek tertentu berdasarkan nomor (contoh: 1, 3, 5-8)
 [8] Bersihkan projek TIDAK AKTIF saja (> 30 hari tidak diedit)
 [s] Bersihkan CACHE GLOBAL SISTEM & DEVELOPER (~24 GB: NPM, Gradle, Chrome, dll)
 [d] Rapikan & Kelola folder DOWNLOADS (Kategori, Duplikat, Hapus Sampah)
 [t] Ganti Mode Hapus: [Permanent Delete / macOS Trash]
 [l] Lihat isi file log (.log) langsung di terminal
 [r] Scan ulang direktori
 [q] Keluar
```

---

## 🛠️ Membuat Perintah Shortcut (Alias) di Mac / Zsh

Agar bisa dipanggil dari mana saja cukup dengan mengetik `cleanproject` atau `cleandownloads`:

1. Buka konfigurasi Zsh Anda:
   ```bash
   nano ~/.zshrc
   ```
2. Tambahkan baris alias berikut di bagian paling bawah:
   ```bash
   alias cleanproject="python3 /Users/mbairm12020/Documents/projek/cleaner/cleaner.py"
   alias cleandownloads="python3 /Users/mbairm12020/Documents/projek/cleaner/organize_downloads.py"
   ```
3. Simpan dan muat ulang:
   ```bash
   source ~/.zshrc
   ```
