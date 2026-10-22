# 🚀 Developer Project Cleaner

Aplikasi Python modern, cepat, dan aman untuk memindai serta membersihkan berkas cache, build artifacts, `node_modules`, dan cache sistem developer dari Mac Anda dalam sekali jalan.

Mendukung otomatisasi:
- **Flutter / Dart**: Menjalankan `flutter clean`, membersihkan `build/`, `.dart_tool/`, `.flutter-plugins`, build cache Android/iOS.
- **Node.js / Web**: Menghapus `node_modules/`, `.next/`, `.nuxt/`, `dist/`, `.output/`, `.turbo/`, `.cache/`, dll.
- **Python**: Menghapus `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, build & egg-info (dan opsional `.venv`).
- **Android / Gradle**: Menghapus `.gradle/`, `build/`, `app/build/`.
- **Xcode / iOS / macOS**: Menghapus `Pods/`, `DerivedData/`, `.build/`.
- **Rust / Cargo**: Menjalankan `cargo clean`, menghapus `target/`.
- **System & Developer Global Caches**: Membersihkan cache global `~/.npm` (5.8 GB), `~/.gradle/caches` (5.3 GB), Xcode DerivedData (1.1 GB), Chrome Cache (4.2 GB), Telegram Cache (880 MB), dll.
- **Pencatatan Log (`.log`)**: Semua berkas & folder yang dihapus otomatis dicatat rapi ke dalam file `.log`.

---

## 🌟 Fitur Utama

1. **Zero External Dependencies**: Berjalan langsung menggunakan bawaan Python 3 tanpa perlu `pip install`.
2. **Pencatatan Riwayat (`.log`) Otomatis**: Setiap item yang dihapus dicatat lengkap dengan timestamp, path lengkap, ukuran, dan modenya ke `cleaner.log`.
3. **Pembersih Cache Global Sistem (System Data)**: Mampu mendeteksi dan membersihkan puluhan gigabyte cache developer & aplikasi yang tersimpan di `~/Library` dan folder `~/.`.
4. **Terminal UI Interaktif**: Tabel ringkas dengan warna ANSI, menampilkan ukuran disk yang dapat dihemat per projek dan total GB.
5. **Safety First**:
   - **Mode Dry-Run (`--scan`)**: Analisa dan lihat kapasitas disk tanpa menghapus apapun.
   - **Dukungan macOS Trash (`--trash`)**: Pindahkan folder ke Tempat Sampah (*macOS Bin*) alih-alih dihapus permanen agar aman jika ingin di-*restore*.
   - **Filter Umur Projek (`--days 30`)**: Hanya bersihkan projek yang sudah tidak aktif / tidak diedit dalam X hari.
   - **Konfirmasi Bertingkat**: Selalu meminta konfirmasi sebelum melakukan penghapusan data.
6. **Fleksibel**: Bisa dijalankan secara interaktif (menu pilihan nomor) atau langsung lewat argumen CLI.

---

## ⚡ Cara Menjalankan

### 1. Mode Interaktif (Paling Nyaman)
Cukup jalankan perintah berikut dari terminal:
```bash
python3 cleaner.py
```
*(Atau `./run.sh`)*

Menu interaktif menyediakan opsi:
```text
╔════════════════════════════════════════════════════════════════════════════╗
║                     🚀 PROJECT CLEANER FOR DEVELOPERS                      ║
║        Flutter (clean) • Node (node_modules) • Python • Gradle • iOS        ║
╚════════════════════════════════════════════════════════════════════════════╝

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
 [t] Ganti Mode Hapus: [Permanent Delete / macOS Trash]
 [l] Lihat isi file log (.log) langsung di terminal
 [r] Scan ulang direktori
 [q] Keluar
```

---

### 2. Mode Perintah Cepat (CLI Flags)

#### Bersihkan Cache Sistem & Developer Global:
```bash
python3 cleaner.py --system-caches
```

#### Analisis Ukuran Saja (Dry-Run / Tanpa Menghapus):
```bash
python3 cleaner.py --scan
```

#### Bersihkan Projek Flutter:
```bash
python3 cleaner.py --flutter
```

#### Bersihkan Projek Node.js (`node_modules` & build):
```bash
python3 cleaner.py --node
```

#### Bersihkan Cache Python:
```bash
python3 cleaner.py --python
```

#### Bersihkan Projek yang Tidak Aktif Lebih dari 30 Hari:
```bash
python3 cleaner.py --days 30
```

#### Pindahkan ke macOS Trash (Tempat Sampah) Alih-alih Hapus Permanen:
```bash
python3 cleaner.py --node --trash
```

#### Tentukan Lokasi File Log Khusus:
```bash
python3 cleaner.py --node --log-file ~/riwayat_cleaner.log
```

#### Otomatis Ya (Non-Interaktif / CI / Cron Script):
```bash
python3 cleaner.py --all -y
```

---

## 🛠️ Membuat Perintah Shortcut (Alias) di Mac / Zsh

Agar bisa dipanggil dari mana saja cukup dengan mengetik `cleanproject`:

1. Buka konfigurasi Zsh Anda:
   ```bash
   nano ~/.zshrc
   ```
2. Tambahkan baris alias berikut di bagian paling bawah:
   ```bash
   alias cleanproject="python3 /Users/mbairm12020/Documents/projek/cleaner/cleaner.py"
   ```
3. Simpan dan muat ulang:
   ```bash
   source ~/.zshrc
   ```
4. Sekarang Anda bisa mengetik `cleanproject` kapan saja dari folder mana pun!
