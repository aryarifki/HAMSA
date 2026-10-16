# HAMSA OSINT Intelligence Framework 🪬

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016%20%7C%20MD3-black.svg)](https://nextjs.org)
[![Zero External Core Deps](https://img.shields.io/badge/Core%20Dependencies-0%20(Pure%20Stdlib)-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Autonomous Reconnaissance, Recursive Entity Correlation, Continuous Exposure Monitoring, and Material Design 3 Knowledge Network.**

**HAMSA** adalah platform intelijen sumber terbuka (*Open Source Intelligence / OSINT*) generasi berikutnya yang dirancang untuk mengumpulkan, mengkorelasikan secara otonom, dan memvisualisasikan jejak digital entitas publik (Username, Email, Nomor Telepon, dan Metadata Foto) ke dalam peta jaringan relasional (*knowledge graph*).

Dibangun dengan arsitektur **Zero Mandatory External Dependencies** (berjalan murni di atas pustaka standar Python), HAMSA dapat beroperasi sebagai CLI mandiri yang sangat cepat, atau sebagai platform web enterprise berkelas tinggi dengan antarmuka **Material Design 3 (MD3)**, persistensi graf **Neo4j**, sistem pemantauan berkelanjutan (**Continuous Surveillance**), dan engine ekspor laporan forensik otomatis.

---

## 🏛️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       HAMSA OSINT INTELLIGENCE SUITE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ FRONTEND ]  Next.js 16 (App Router) • MD3 Warm Obsidian • Apache ECharts │
│                SSE Real-Time Stream • Case Dossier Manager • Timeline View  │
│                Zustand Store • SWR Caching • Standalone Dossier Print View  │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ REST API ]  Port 8888 (Auto Safe-Port, Strict Exemption on Port 8080)    │
│                Endpoints: /api/scan, /api/scan/stream (SSE), /api/cases,    │
│                /api/timeline, /api/evidence, /api/watchlist, /api/report    │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ CORE ]      Agent Brain (Recursive Planner & Garbage Token Pruning)      │
│                CaseManager (Multi-Case Workspace & Forensic Notes/Evidence) │
│                Two-Tier Cache (L1 Memory LRU 0ms + L2 Redis Fallback)       │
│                Graph Persistence (MemoryGraphBackend / Neo4jGraphBackend)   │
│                ScanDiffEngine (Cross-Scan Perimeter Drift & Threat Scoring) │
│                ReportGenerator (Executive Summary, Timeline & HTML Dossier) │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ OPSEC ]     Tor SOCKS5 Circuit Routing • Wayback Machine Passive Lookup  │
│                Modern Browser Client Hints Spoofing (Sec-Ch-Ua) & Jitter    │
├─────────────────────────────────────────────────────────────────────────────┤
│  [ PLUGINS ]   • Username: WhatsMyName Community DB (690+ Platforms)        │
│                • Email: XposedOrNot Public Breaches & HudsonRock Malware    │
│                • Phone: E.164 Normalizer, Carrier ID & PhoneInfoga Dorks    │
│                • EXIF: Pure-Python GPS Geocoding & Camera Identification    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Fitur-Fitur Unggulan

### 1. Autonomous Agent Brain & Rekursi Cerdas
Orchestrator tidak hanya mengumpulkan data secara statis, melainkan memiliki **AgentBrain** yang mengevaluasi graph secara real-time:
- Menganalisis entitas turunan (misal: username yang didapat dari email breach, atau nama asli dari profil GitHub).
- **Garbage Token Filter**: Secara otomatis membuang token sampah seperti `unknown`, `null`, `admin`, `login` agar penyelidikan tidak melebar tanpa arah.
- Melanjutkan investigasi **Ronde Kedua (Depth 2+)** secara otomatis untuk memetakan subjek secara mendalam.

### 2. Dynamic Source Manager (690+ Situs)
Alih-alih menggunakan daftar platform hardcoded, modul `SourceManager` secara otomatis mengunduh, memvalidasi, dan meng-cache definisi dari repositori komunitas global (WhatsMyName). Memeriksa platform media sosial, forum, repositori kode, dan platform profesional.

### 3. Pluggable Graph Backend (In-Memory & Neo4j)
- **`MemoryGraphBackend` (Default)**: Berjalan murni di memori RAM tanpa instalasi database tambahan. Dilengkapi pendeteksi atribut bersama (*shared attributes* seperti shared IP, carrier, email).
- **`Neo4jGraphBackend` (Enterprise)**: Mengalirkan data ke kluster Neo4j melalui Cypher query (`MATCH`, `MERGE`). Aktifkan cukup dengan flag `--neo4j` atau `HAMSA_GRAPH_BACKEND=neo4j`.

### 4. Continuous Surveillance & Webhook Alerting
Ubah OSINT reaktif menjadi **pemantauan proaktif**:
- **Watchlist Registry**: Daftarkan target subjek ke dalam daftar pantau (`~/.hamsa/watchlist.json`).
- **ScanDiffEngine**: Menghitung *perimeter drift* antar pemindaian:
  - Entitas baru yang ditemukan (`+added`).
  - Entitas yang ditutup/dihapus (`-removed`).
  - Perubahan atribut/metadata profil.
  - Kebocoran data baru berkategori kritis (**CRITICAL BREACH**).
- **Webhook Dispatcher**: Mengirimkan kartu notifikasi ancaman berformat rapi ke **Discord**, **Slack**, atau **Telegram Bot API**.

### 5. Advanced Forensic Reporting Engine
Menghasilkan laporan investigasi berstandar dewan direksi (*board-ready*) atau penegak hukum:
- **Executive Summary**: Ringkasan naratif risiko ancaman, akun media sosial terverifikasi, dan jejak telekomunikasi.
- **Chronological Timeline Analysis**: Mengurutkan waktu pengambilan foto (EXIF), tahun insiden kebocoran data, dan timestamp infeksi malware ke dalam garis waktu kronologis.
- **Standalone HTML & Markdown**: Menghasilkan satu file HTML mandiri dengan tema Material Design 3 dan `@media print` untuk cetak dokumen PDF resmi.

### 6. OPSEC & Stealth Routing Engine
- **Tor SOCKS5 Routing (`--tor`)**: Mengalirkan seluruh lalu lintas investigasi melalui jaringan Tor SOCKS5 (`socks5://127.0.0.1:9050`).
- **Passive Wayback Machine Archival (`--wayback`)**: Memeriksa ketersediaan halaman di arsip web (`archive.org/wayback/available`) secara pasif tanpa menyentuh server target asli.
- **Modern Fingerprint Emulation**: Mengirimkan header browser Chromium modern (`Sec-Ch-Ua`, `Sec-Fetch-Dest`, `Sec-Fetch-Mode`) dengan penundaan acak (*jitter*).

### 7. Keamanan Port 8080 (Strict Port Isolation)
Sistem memiliki mekanisme keamanan port ketat: server web HAMSA **tidak akan pernah menggunakan port 8080** (yang dicadangkan untuk crawler lokal seperti `ocrawler`). Port default backend adalah **8888** dan frontend adalah **3000**.

### 8. Real-Time Event Streaming (SSE Radar Detection)
Menyediakan pengalaman investigasi langsung (*alive radar experience*):
- Endpoint `/api/scan/stream` mengalirkan event **Server-Sent Events (SSE)** murni berbasis Python Standard Library (`BaseHTTPRequestHandler` buffer flush).
- Setiap kali plugin menemukan entitas baru, event `node_added` dan `edge_added` dipancarkan secara instan.
- Frontend Apache ECharts langsung menganimasikan radar pings dan memunculkan node ke visual graph secara asinkron tanpa menunggu seluruh scan selesai.

### 9. Multi-Case Investigation Dossiers (`CaseManager`)
Pemisahan ruang kerja investigasi (*case isolation*) setara Maltego / Lampyre:
- Menyimpan setiap kasus investigasi secara terisolasi di `~/.hamsa/cases/<case_id>.json`.
- Mendukung multi-subjek, catatan forensik khusus investigator, tag status (Active, In-Review, Closed), serta manajemen bukti digital (*evidence snapshots*).
- Memungkinkan beralih antar kasus secara instan tanpa kehilangan histori graf dan konfigurasi target.

### 10. Interactive Graph Manipulation & Chronoforensic Timeline
- **Node Pivoting**: Klik kanan atau pilih node apapun di graf (misal: Email baru ditemukan) untuk langsung menjalankan pemindaian rekursif (*Pivot / Scan This Entity*).
- **Investigator Marking**: Menandai entitas target utama (*Primary Suspect* dengan halo merah menyala, *Verified Lead*, *False Positive*).
- **Interactive Search Dimming**: Pencarian entitas dinamis meredupkan node non-relevan (opacity 15%) dan menerangi node target.
- **Chronoforensic Timeline**: Halaman khusus `/timeline` yang mengekstrak dan mengurutkan seluruh metadata waktu (EXIF capture, breach years, infeksi malware) dengan filter kategori dan tautan kembali ke graf.

### 11. Spatial Filtering & Geofencing Intelligence Engine
Engine penyaringan spasial dan analisis geofencing berbasis komputasi geometri murni pustaka standar Python:
- **Haversine Circular Radius Filter**: Menghitung jarak lingkaran besar (*Great-Circle Distance*) $R = 6371.0088\text{ km}$ untuk menemukan entitas foto/lokasi dalam radius tertentu (misal: $\le 5\text{ km}$ dari TKP / target).
- **Axis-Aligned Bounding Box (AABB)**: Menyaring koordinat GPS dalam kotak pembatas geografis (`min_lat`, `max_lat`, `min_lon`, `max_lon`) dengan dukungan pelintasan meridian ke-180 (*Antimeridian*).
- **Ray-Casting Point-in-Polygon (PIP)**: Menguji apakah koordinat GPS berada di dalam area poligon bebas/kompleks (*arbitrary geofence polygon*) menggunakan teorema kurva Jordan (*Jordan Curve Theorem*) tanpa dependensi berat C-extension (seperti GDAL atau Shapely).
- **Automated GPS Extraction**: Mendeteksi koordinat lintang/bujur otomatis dari metadata EXIF kamera JPEG/TIFF, IP Geolocation, dan node tipe `TargetType.LOCATION`.

### 12. Multi-Source Intelligence Engines & Keyless Recon (14 Repositories Integration)
Integrasi logika, algoritma analitik, dan kapabilitas OSINT tingkat tinggi yang diadaptasi dari repositori intelijen siber terkemuka:
- **Instagram Unauthenticated Contact Lookup** (*toutatis* & *InstagramPrivSniffer*): Mengekstraksi informasi kontak terselubung (*masked email* `t***s@g***.com` & *masked phone* `+62 812 •••• ••89`) secara publik tanpa memerlukan akun login.
- **Keyless Shodan InternetDB Recon** (*theHarvester*): Memetakan port terbuka, CPE layanan, hostnames, dan kerentanan CVE aktif sebuah IP target tanpa memerlukan Shodan API Key berbayar.
- **Certificate Transparency Subdomain Discovery** (*Amass* & *crt.sh*): Mengumpulkan seluruh rekaman subdomain domain organisasi dari log transparansi sertifikat SSL/TLS publik.
- **Free IP Geolocation & ASN Resolver** (*cipher387/API-s-for-OSINT*): Melakukan resolusi IP target ke koordinat lintang/bujur, negara, kota, dan Autonomous System Number (ASN) dengan relasi geospasial otomatis.
- **Dynamic Baseline Control Comparator** (*tookie-osint*): Mengeliminasi false positive pada scanning username (soft-404 dengan status 200 OK) dengan membandingkan respons target terhadap string acak baseline non-existent.
- **Persona Resolution Engine** (*nox-framework*): Algoritma *Union-Find / Disjoint-Set* untuk menggabungkan fragmen entitas yang tersebar (username, email, telepon, media sosial) menjadi kluster profil identitas tunggal (*Unified Personas*).
- **FAIR-Aligned Quantitative Risk Scoring** (*nox-framework*): Engine kalkulasi ancaman 0–100 berdasarkan eksposur kebocoran data, infeksi malware, kerentanan CVE kritis, dan port berisiko tinggi.
- **Geometric 3-Circle Trilateration** (*IvanGlinkin/CCTV*): Penentuan estimasi posisi koordinat target menggunakan metode perpotongan 3 lingkaran spasial tertutup (*closed-form 2D trilateration*).
- **Username Permutation & Variation Synthesis** (*blackbird*): Menghasilkan variasi handle username secara cerdas menggunakan permutasi separator (`.`, `_`, `-`) dan afiks (`real_`, `_official`, `01`, dll).
- **Corporate Employee Cleansing & Pattern Synthesizer** (*LinkedInDumper*): Membersihkan gelar formal/akademik (`Prof.`, `Dr.`, `M.Eng.`, `Ph.D.`) dan mensintesis pola email korporat standar (`first.last@domain.com`, `flast@domain.com`, dll).
- **Thematic Topic Clustering** (*carrot2*): Pengelompokan semantik entitas target berdasarkan kata kunci dominan dan minat topik.
- **Resilience Circuit Breaker & Adaptive Delay** (*atdork*): Proteksi kegagalan jaringan eksternal dengan auto-trip circuit breaker dan backoff jitter adaptif.

---

## 🚀 Panduan Penggunaan CLI

### 1. Bantuan & Daftar Opsi Lengkap
```bash
python3 -m hamsa.cli --help
```

### 2. Investigasi Username (Multi-Platform Hunter)
```bash
# Investigasi username dengan scan 50 situs terpopuler & ekspor laporan
python3 -m hamsa -u torvalds --report laporan_torvalds.html

# Investigasi username ke seluruh 690+ database komunitas dengan rekursi
python3 -m hamsa -u target_username --all-sites --depth 2 --html graph.html
```

### 3. Investigasi Email Terhadap Data Breach & Malware
```bash
# Cek kebocoran data (XposedOrNot & HudsonRock) dan simpan ke JSON & HTML
python3 -m hamsa -e victim@target.com --depth 2 --json raw_intel.json --report dossier.html
```

### 4. Investigasi Nomor Telepon & Caller Intelligence
```bash
# Parser E.164, deteksi operator, jenis jaringan, dan dork PhoneInfoga
python3 -m hamsa -p +628123456789 --csv phone_intel.csv --html phone_graph.html
```

### 5. Investigasi Multi-Target Simultan
```bash
# Menghubungkan email, username, telepon, dan foto ke dalam satu knowledge graph
python3 -m hamsa -u target_user -e target@domain.com -p 08123456789 -i suspect.jpg --report master_dossier.html
```

### 6. Pemantauan Berkelanjutan (Continuous Surveillance Watchlist)
```bash
# 1. Tambahkan target ke watchlist
python3 -m hamsa --watchlist-add "target_executive" --watchlist-type username

# 2. Lihat daftar target yang sedang dipantau
python3 -m hamsa --watchlist-list

# 3. Jalankan siklus pengecekan otomatis dengan alert Webhook (Discord / Slack / Telegram)
python3 -m hamsa --check-watchlist --webhook "https://discord.com/api/webhooks/..."

# 4. Hapus target dari watchlist
python3 -m hamsa --watchlist-remove "target_executive" --watchlist-type username
```

### 7. Penggunaan Fitur OPSEC & Stealth
```bash
# Melewati rute Tor SOCKS5 dan verifikasi Wayback Machine pasif
python3 -m hamsa -u sensitive_target --tor --wayback --report stealth_dossier.html
```

---

## 🌐 Menjalankan Enterprise Platform (Debian & Ubuntu Ready)

HAMSA menyediakan deployment otomatis (*zero-friction bootstrap*) yang dapat dijalankan secara instan di **Debian 11/12** maupun **Ubuntu 20.04/22.04/24.04 LTS**:

### Metode 1: Docker Compose Enterprise (Direkomendasikan)
Menyalakan seluruh stack (PostgreSQL 16, Redis 7, Backend FastAPI ASGI, dan Next.js MD3 Frontend) dalam satu perintah:

```bash
# 1. Salin template konfigurasi lokal
cp .env.example .env

# 2. (Opsional) Sesuaikan POSTGRES_PASSWORD atau kredensial di file .env

# 3. Jalankan seluruh kontainer di background
docker compose up -d
```
- **Next.js Web Frontend**: `http://localhost:3000`
- **Enterprise REST API**: `http://localhost:8888`
- **Interactive Swagger Docs**: `http://localhost:8888/docs`
- **PostgreSQL 16 Database**: `localhost:5432`

---

### Metode 2: Bare-Metal Server (Debian / Ubuntu Native)
Jika menjalankan langsung di VPS atau server tanpa Docker:

```bash
# 1. Jalankan script setup otomatis (memeriksa paket Debian/Ubuntu & venv)
chmod +x setup.sh start.sh
./setup.sh

# 2. Jalankan Enterprise Backend Service
./start.sh
```

---

### Metode 3: Standalone Zero-Dependency (CLI Mode)
Jika hanya ingin menjalankan investigasi lokal cepat tanpa PostgreSQL eksternal (otomatis menggunakan SQLite & L1 Memory Cache):

```bash
# Menjalankan server backend lokal
python3 -m hamsa --serve --port 8888

# Menjalankan frontend Next.js
cd frontend && npm install && npm run dev
```

---

## 📡 Dokumentasi REST API

| Method | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Login investigator & mendapatkan token JWT akses (`Bearer`). |
| `GET` | `/api/auth/me` | Profil investigator dan hak akses/peran (*role*). |
| `GET` | `/api/auth/audit` | Buku besar audit forensik digital (*Chain of Custody*). |
| `GET/POST`| `/api/auth/users` | Manajemen akun investigator (khusus peran Admin). |
| `GET` | `/api/graph` | Mengambil seluruh node dan edge dari knowledge graph aktif (opsional: `?case_id=<id>`). |
| `POST` | `/api/graph/path` | **Shortest Path Correlation**: Menemukan jalur relasi terpendek antar 2 entitas subjek. |
| `GET` | `/api/graph/centrality` | **Centrality Scoring**: Menghitung simpul kunci koordinator & *bridge brokerage*. |
| `GET` | `/api/graph/clusters` | **Cluster Detection**: Mengelompokkan sub-jaringan cincin tersangka yang terisolasi. |
| `POST` | `/api/graph/spatial-filter` | **Spatial Geofencing Filter**: Memfilter koordinat GPS (EXIF/Location) dengan radius Haversine, Bounding Box (AABB), atau Poligon Ray-Casting. |
| `POST` | `/api/graph/trilaterate` | **Geometric 3-Circle Trilateration**: Menghitung estimasi koordinat target (Lat/Lon) dari 3 titik referensi lingkaran (`lat`, `lon`, `distance_km`). |
| `GET` | `/api/graph/personas` | **Disjoint-Set Persona Resolution**: Mengelompokkan identitas terfragmentasi menjadi kluster persona terpadu (*Unified Personas*). |
| `GET` | `/api/graph/risk-score` | **FAIR-Aligned Quantitative Risk Scoring**: Menghitung skor risiko terbobot (0–100) berdasarkan CVE, malware, kebocoran data, dan port terbuka. |
| `GET` | `/api/graph/thematic-clusters` | **Thematic Topic Clustering**: Mengelompokkan node berdasarkan tema topik dan kata kunci semantik dominan. |
| `GET` | `/api/timeline` | Mengekstrak rekaman jejak kronologis (EXIF, breach dates, malware timestamps) per kasus. |
| `POST` | `/api/scan` | Memulai investigasi baru (`username`, `email`, `phone`, `depth`, `all_sites`, dll). |
| `GET` | `/api/scan/stream` | **Server-Sent Events (SSE)**: Streaming radar pemindaian real-time (`node_added`, `edge_added`). |
| `GET` | `/api/scan/history` | Riwayat status eksekusi scan background (*persistent scan state*). |
| `GET` | `/api/cases` | Mengambil daftar seluruh investigasi kasus (*case dossiers*). |
| `POST` | `/api/cases` | Membuat kasus investigasi baru (`title`, `description`, `tags`). |
| `GET` | `/api/cases/<id>` | Mengambil detail kasus lengkap beserta grafik dan bukti digital. |
| `POST` | `/api/cases/<id>/annotate`| Menambahkan marking/tag investigasi pada node tertentu (`Primary Suspect`, `Verified Lead`). |
| `POST` | `/api/cases/<id>/notes` | Menyimpan catatan forensik investigator untuk berkas perkara. |
| `POST` | `/api/evidence/capture` | Menyimpan bukti digital (*forensic evidence snapshot*) ke dalam berkas kasus. |
| `GET` | `/api/export` | **Interoperabilitas Global**: Ekspor ke format **GraphML** (Gephi/Maltego), **STIX 2.1**, CSV, atau JSON. |
| `GET` | `/api/report?format=html` | Mengunduh laporan dossier forensik berformat HTML cetak atau Markdown (`?format=markdown`). |
| `POST` | `/api/report` | Membuat laporan kustom berdasarkan parameter JSON (`format`, `title`). |
| `GET` | `/api/watchlist` | Mengambil daftar seluruh target dalam surveillance watchlist. |
| `POST` | `/api/watchlist` | Menambah (`action: "add"`) atau menghapus (`action: "remove"`) subjek dari watchlist. |
| `POST` | `/api/watchlist/check` | Menjalankan pemindaian diff perimeter dan mengembalikan skor drift. |
| `POST` | `/api/cypher` | Menjalankan query graph Cypher langsung ke backend persistent Neo4j. |
| `GET` | `/api/cache/stats` | Melihat metrik efisiensi L1 Memory LRU Cache dan L2 Redis. |
| `POST` | `/api/cache/clear` | Mengosongkan data cache L1/L2. |
| `POST` | `/api/reset` | Mereset graph dan mengosongkan cache sistem. |
| `POST` | `/api/update-sources` | Sinkronisasi database komunitas WhatsMyName terbaru (690+ situs). |

---

## 🔌 Mengembangkan Plugin Baru

Membuat plugin baru sangat sederhana. Buat berkas Python di dalam folder `hamsa/plugins/<kategori>/`:

```python
from hamsa.core.models import PluginMetadata, TargetType, PluginResult, RelationType
from hamsa.plugins.base import BasePlugin

class CustomIntelPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="custom_osint_module",
        version="1.0.0",
        author="Your Name",
        description="Pemeriksaan intelijen kustom.",
        target_types=[TargetType.USERNAME],
    )

    async def run(self, target: str, target_type: TargetType, context=None) -> PluginResult:
        # Buat entity node baru
        node = self.create_node(
            node_id=f"custom:{target}",
            node_type=TargetType.GENERIC,
            value="Informasi penting yang ditemukan",
            label=f"Hasil: {target}",
            attributes={"platform": "InternalService", "confidence": 0.95},
        )
        return PluginResult(
            plugin_name=self.metadata.name,
            success=True,
            nodes=[node],
            edges=[],
            logs=["Modul kustom berhasil dieksekusi."],
        )
```
Daftarkan plugin Anda di `hamsa/core/orchestrator.py` pada metode `_register_default_plugins`.

---

## 🧪 Pengujian Unit & Verifikasi

Seluruh logika inti, parser EXIF, parser telepon, engine korelasi, diff perimeter, cache ganda, dan proteksi port diverifikasi dengan suite pengujian unit otomatis:

```bash
# Menjalankan seluruh pengujian unit Python
python3 -m unittest discover -s tests -p "test_*.py" -v

# Memverifikasi build frontend Next.js
cd frontend && npm run build
```

---

## ⚖️ Lisensi & Etika Penggunaan
Proyek ini dilisensikan di bawah **MIT License**.

> **Peringatan Etika**: HAMSA dirancang secara ketat untuk investigasi sumber terbuka yang sah, riset keamanan siber defensif, respon insiden, dan penegakan hukum. Dilarang keras menggunakan perangkat lunak ini untuk aktivitas ilegal, pelecehan (*doxxing*), atau pelanggaran privasi.
