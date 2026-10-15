# HAMSA Intelligence Web Application 🪬

> **Material Design 3 (MD3) Cyber Reconnaissance Dashboard & Knowledge Network Visualizer**

Built with **Next.js 16 (App Router & Turbopack)**, **Tailwind CSS**, **Apache ECharts**, and **Zustand**. Designed with the exact tokens, color scheme, and interaction patterns inspired by InvestOwl and Google's Material You (MD3) design system.

---

## 🎨 Design System & Theming

- **Light Surface**: `#F9EDE1` (Warm Sand), Container: `#F3E7DC`, Text: `#211D1A`
- **Dark Surface**: `#141210` (Deep Obsidian), Container: `#211D1A`, Text: `#EBE0D9`
- **Primary Accent**: `#FFB879` (Electric Amber / Cyber Gold)
- **Container Outlines**: `#52443C` (40% subtle borders)
- **Radar Pulse Overlay**: Fullscreen animated canvas with phased reconnaissance scan step tracker.

---

## 🚀 Key Modules & Routes

| Route | Page | Purpose |
| :--- | :--- | :--- |
| `/` | **Target Roster** | Executive dashboard displaying all investigated subjects, risk badges, quick metrics, and quick-add reconnaissance dialog. |
| `/graph` | **Knowledge Network** | Interactive Apache ECharts graph visualizer supporting Force-Directed and Circular topology, real-time node filtering, entity detail drawers, and image export. |
| `/target/[id]` | **Deep Dossier** | Comprehensive intelligence dossier for a specific target with tabs for Discovered Accounts, Breaches & Malware, Phone & Contacts, Raw Metadata, and one-click **Export Dossier** to standalone HTML. |
| `/breaches` | **Breaches & Malware** | Dedicated threat registry tracking all data breach incidents and Infostealer malware logs across subjects. |
| `/contacts` | **Phone & Telecom** | Telecommunication directory showcasing verified E.164 numbers, cellular carriers, and crowd-sourced caller tags. |

---

## 🛠️ Setup & Development

### Prerequisites
- Node.js 18.0+ (Tested on Node.js 24)
- npm 9+

### Installation
```bash
cd frontend
npm install
```

### Development Server
```bash
npm run dev
# The frontend starts at http://localhost:3000
```

> **Note on Port Safety**: The backend REST API defaults to `http://localhost:8888`. Port **8080** is strictly avoided and forbidden across all HAMSA services.

### Production Build
```bash
npm run build
npm start
```
Compiles statically with Turbopack and verifies all TypeScript types.
