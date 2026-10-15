# Hamsa OSINT Framework 🪬

> **Modular, Lightweight, and Zero-Setup OSINT & Entity Correlation Framework**

Hamsa adalah framework Open Source Intelligence (OSINT) yang dirancang untuk mengumpulkan, mengkorelasikan, dan memvisualisasikan jejak digital entitas publik (Email, Username, Nomor Telepon, dan Metadata Foto) ke dalam satu peta jaringan (*knowledge graph*).

---

## 🚀 Fitur Utama (Fase 1 Prototype)

* **Zero External Dependencies by Default:** Berjalan langsung di atas Python 3.10+ murni menggunakan pustaka standar (`asyncio`, `urllib`, `dataclasses`, `argparse`).
* **Modular Plugin Architecture:** Setiap kapabilitas investigasi diisolasi dalam plugin terpisah (`hamsa/plugins/`).
* **Multi-Target Ingestion & Cross-Linking:** Dapat menerima beberapa target sekaligus dan secara otomatis membuat relasi korelasi (*associated with*).
* **Standalone Interactive HTML Graph:** Menghasilkan visualisasi graf interaktif modern berbasis Vis.js yang dapat dibuka langsung di browser tanpa memerlukan server database Neo4j.
* **JSON Raw Intelligence Export:** Ekspor struktur data graf entitas dan relasi untuk analisis lanjutan.

---

## 📦 Struktur Proyek

```
hamsa/
├── hamsa/
│   ├── cli.py                     # Entry point antarmuka CLI
│   ├── __main__.py                # Eksekutor modul (python -m hamsa)
│   ├── core/
│   │   ├── models.py              # Skema EntityNode, RelationEdge, PluginResult
│   │   ├── orchestrator.py        # Mesin dispatch plugin asinkron & korelasi
│   │   └── graph.py               # In-memory graph & visualizer HTML/JSON
│   ├── plugins/
│   │   ├── base.py                # Kontrak abstrak BasePlugin
│   │   ├── username/
│   │   │   └── fast_checker.py    # Scanner multi-platform username
│   │   ├── email/
│   │   │   └── xposedornot_breach.py # Korelasi kebocoran data XposedOrNot
│   │   ├── phone/
│   │   │   └── phone_parser.py    # Parser E.164, negara & operator seluler
│   │   └── exif/
│   │       └── photo_metadata.py  # Ekstraktor EXIF kamera & koordinat GPS
│   └── utils/
│       ├── http.py                # HTTP client async dengan rotasi User-Agent & jitter
│       └── formatters.py          # Output terminal & banner
└── tests/
    └── test_core.py               # Unit test otomatis
```

---

## 🛠️ Panduan Penggunaan CLI

### 1. Melihat Plugin yang Terdaftar
```bash
python3 -m hamsa --list-plugins
```

### 2. Investigasi Username (Termasuk Auto-Scan Rekursif Ronde Kedua)
Secara default, Hamsa akan mengekstrak nama asli atau handle baru dari profil yang ditemukan, lalu otomatis menjalankan **Ronde Kedua (Depth 2)** untuk menginvestigasi nama tersebut ke seluruh web:
```bash
python3 -m hamsa -u target_username --depth 2 --html report.html --json report.json
```
Jika hanya ingin menjalankan scan 1 ronde cepat tanpa rekursi:
```bash
python3 -m hamsa -u target_username --no-recursive
```

### 3. Investigasi Email Terhadap Data Breach, Infostealer & Auto-Username Derivation
Mengecek kebocoran database publik (XposedOrNot) dan infeksi malware (Hudson Rock), serta **otomatis mengekstrak username untuk investigasi Ronde Kedua** ke seluruh media sosial:
```bash
python3 -m hamsa -e target@example.com --depth 2 --csv breach_report.csv --html email_report.html
```

### 4. Analisis Nomor Telepon, Line-Type & PhoneInfoga Footprint
Mendeteksi operator, jenis sambungan, link direct WhatsApp/Telegram, dan **PhoneInfoga multi-format search dorks** (Social Footprint, Document Leaks, Directory Queries):
```bash
python3 -m hamsa -p 08123456789 --csv phone_report.csv --html phone_report.html
```

### 5. Investigasi Multi-Target Sekaligus (Korelasi Graf & Ekspor Lengkap)
Menghubungkan email, nomor telepon, dan username secara simultan ke dalam file visual dan spreadsheet CSV:
```bash
python3 -m hamsa -u target_username -e target@example.com -p 08123456789 --csv full_report.csv --html full_investigation.html
```

### 6. Ekstraksi Metadata & Reverse Geocoding GPS Foto
Mengekstrak tipe kamera dan otomatis mengubah koordinat GPS menjadi alamat fisik nyata (Jalan, Kelurahan, Kota, Negara):
```bash
python3 -m hamsa -i sample_photo.jpg --html photo_graph.html
```

---

## 🔌 Cara Membuat Plugin Baru

Cukup buat file baru di dalam direktori `hamsa/plugins/<kategori>/` dan warisi kelas `BasePlugin`:

```python
from hamsa.core.models import PluginMetadata, TargetType, PluginResult, RelationType
from hamsa.plugins.base import BasePlugin

class MyCustomPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="my_custom_checker",
        version="0.1.0",
        author="Contributor Name",
        description="Deskripsi singkat modul Anda.",
        target_types=[TargetType.USERNAME],
    )

    async def run(self, target: str, target_type: TargetType, context=None) -> PluginResult:
        # Logika investigasi
        node = self.create_node(
            node_id=f"custom:{target}",
            node_type=TargetType.GENERIC,
            value="Data yang ditemukan",
            label=f"Custom Result: {target}",
        )
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=[node],
            edges=[],
            logs=["Pemeriksaan custom selesai."],
        )
```

Lalu daftarkan plugin di `hamsa/core/orchestrator.py` (`_register_default_plugins`).

---

## 🧪 Menjalankan Pengujian Unit

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## ⚖️ Lisensi
Proyek ini dirancang di bawah lisensi terbuka (MIT License). Gunakan hanya untuk tujuan edukasi, penelitian keamanan defensif, dan penegakan hukum yang sah.
