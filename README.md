# 🚀 Developer Project Cleaner & Downloads Organizer (Windows & macOS)

Aplikasi Python modern, cepat, dan aman untuk memindai serta membersihkan berkas cache, build artifacts, `node_modules`, cache sistem Windows & Mac, serta **merapikan folder Downloads**.

Mendukung otomatisasi:
- **Flutter / Dart**: Menjalankan `flutter clean`, membersihkan `build/`, `.dart_tool/`, `.flutter-plugins`, build cache Android/iOS.
- **Node.js / Web**: Menghapus `node_modules/`, `.next/`, `.nuxt/`, `dist/`, `.output/`, `.turbo/`, `.cache/`, dll.
- **PHP / Laravel / Composer**: Menghapus `storage/logs/`, `storage/framework/cache/`, `views/`, `sessions/`, `bootstrap/cache/`, `var/cache/`, dan opsi `vendor/`.
- **Go / Golang**: Menghapus file kompilasi `bin/`, `dist/`, `tmp/` (.air), executables, dan menjalankan `go clean`.
- **.NET / C#**: Menghapus folder `bin/`, `obj/`, `.vs/`, `TestResults/`, dan menjalankan `dotnet clean`.
- **Python**: Menghapus `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, build & egg-info (dan opsional `.venv`).
- **Android / Gradle**: Menghapus `.gradle/`, `build/`, `app/build/`.
- **Rust / Cargo**: Menjalankan `cargo clean`, menghapus `target/`.
- **Xcode / iOS / macOS**: Menghapus `Pods/`, `DerivedData/`, `.build/`.
- **Pembersih Cache Sistem Windows & Global Dev**:
  - Windows User Temp (`%TEMP%`)
  - Windows System Temp (`C:\Windows\Temp`)
  - Windows Update Download Cache (`SoftwareDistribution\Download`)
  - Crash Dumps (`AppData\Local\CrashDumps`) & Windows Error Reporting (WER)
  - Google Chrome & Microsoft Edge Browser Caches
  - Gradle Global Cache (`~/.gradle/caches` & wrapper dists)
  - Pip Global Cache, NPM Cache, Composer Cache, NuGet Cache, Go Build Cache
  - Windows Recycle Bin di Drive C: dan Drive D:
- **Dukungan Multi-Drive (Drive C: & D:)**: Memindai seluruh drive sekaligus secara otomatis dengan mengabaikan direktori sistem Windows (`Windows`, `Program Files`, dll).
- **Downloads Folder Organizer & Cleaner**: Merapikan file unduhan ke folder kategori (`Documents`, `Images`, `Spreadsheets`, `Code`, `Installers`, `Archives`, dll), mendeteksi duplikat, serta dilengkapi fitur **UNDO** untuk mengembalikan file ke posisi semula!
- **Pencatatan Log (`.log`)**: Semua berkas & folder yang dihapus otomatis dicatat rapi ke dalam file `.log`.

---

## 🌟 Fitur Utama

1. **Zero External Dependencies**: Berjalan langsung menggunakan pustaka standar Python 3 (`ctypes`, `pathlib`, `shutil`) tanpa perlu `pip install`.
2. **Dukungan Multi-Drive**: Mampu memindai Drive C:, Drive D:, atau semua drive Windows yang terpasang dalam satu tampilan tabel rapi.
3. **Dukungan Windows Recycle Bin & macOS Trash**: Mode `--trash` secara otomatis memindahkan berkas ke Tempat Sampah (*Windows Recycle Bin* menggunakan Win32 API `SHFileOperationW`), sehingga aman jika ingin di-*restore*.
4. **Perapian Folder Downloads dengan Fitur UNDO**: Mengelompokkan file secara cerdas berdasarkan tipe ekstensi dan bisa dibatalkan (*revert*) kapan saja dengan 1 klik.
5. **Pencatatan Riwayat (`.log`) Otomatis**: Setiap item yang dihapus dicatat lengkap dengan timestamp, path lengkap, ukuran, dan modenya ke `cleaner.log`.
6. **Safety First**:
   - **Mode Dry-Run (`--scan`)**: Analisa dan lihat kapasitas disk tanpa menghapus apapun.
   - **Filter Umur Projek (`--days 30`)**: Hanya bersihkan projek yang sudah tidak aktif / tidak diedit dalam X hari.

---

## ⚡ Cara Menjalankan di Windows (PowerShell / CMD)

### 1. Pindai (Scan / Dry-Run) Semua Drive
```powershell
# Pindai SEMUA drive yang terpasang (Drive C: dan Drive D:)
python cleaner.py --all-drives --scan

# Pindai drive spesifik saja
python cleaner.py C:\ --scan
python cleaner.py D:\ --scan

# Pindai daftar drive tertentu
python cleaner.py --drives C,D --scan
```

### 2. Pindai & Bersihkan Cache Sistem Windows & Developer
```powershell
# Buka menu pembersih cache sistem (Windows Temp, Update Download, Chrome, Edge, dll)
python cleaner.py --system-caches

# Bersihkan dan pindahkan ke Recycle Bin
python cleaner.py --system-caches --trash
```

### 3. Pindai Berdasarkan Bahasa Pemrograman / Framework
```powershell
# Bersihkan projek Flutter saja di Drive C dan D
python cleaner.py --all-drives --flutter --scan

# Bersihkan projek Node.js (node_modules)
python cleaner.py --all-drives --node --scan

# Bersihkan projek PHP / Laravel (storage/logs, cache)
python cleaner.py --all-drives --php --scan

# Bersihkan projek Go / Golang
python cleaner.py --all-drives --go --scan

# Bersihkan projek .NET / C#
python cleaner.py --all-drives --dotnet --scan

# Bersihkan cache Python (__pycache__)
python cleaner.py --all-drives --python --scan
```

### 4. Menu Interaktif
Jalankan tanpa argumen atau dengan menentukan folder:
```powershell
python cleaner.py
```
Pilihan tindakan di menu interaktif:
* `[1]` Bersihkan SEMUA projek
* `[2]` Bersihkan projek FLUTTER
* `[3]` Bersihkan projek NODE.JS
* `[4]` Bersihkan cache PYTHON
* `[5]` Bersihkan projek PHP / LARAVEL
* `[6]` Bersihkan projek GRADLE / ANDROID
* `[7]` Bersihkan projek .NET / C#
* `[8]` Bersihkan projek GO / GOLANG
* `[9]` Pilih nomor projek tertentu
* `[0]` Bersihkan projek tidak aktif (> 30 hari)
* `[s]` Bersihkan CACHE GLOBAL SISTEM (Temp, Update, Browser, dll)
* `[d]` Kelola & Rapikan folder DOWNLOADS
* `[w]` Beralih memindai SEMUA Drive Windows (C: & D:)
* `[c]` Ganti Target Folder / Drive
* `[t]` Ganti Mode Hapus (Recycle Bin / Hapus Permanen)
* `[l]` Lihat riwayat pembersihan di file `.log`
* `[r]` Scan ulang direktori
* `[q]` Keluar

---

## 📁 Merapikan Folder Downloads

```powershell
# Buka antarmuka interaktif Downloads Organizer
python organize_downloads.py

# Simulasi preview tanpa memindahkan file (Dry-Run)
python organize_downloads.py --dry-run

# Rapikan otomatis ke folder kategori
python organize_downloads.py --auto

# Batalkan perapian terakhir dan kembalikan posisi file semula (UNDO)
python organize_downloads.py --undo
```
