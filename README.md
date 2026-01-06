# 🎵 ToneMix Pro v1.0

**Professional Music Analysis & Management Software for DJs**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg)

ToneMix is an open-source, professional-grade music library manager and analysis tool. Designed to bridge the gap between production and performance, it offers robust metadata handling, precise key/BPM detection, and high-quality transcoding for CDJ workflows.

---

## ✨ Key Features

### 🎧 Professional Library Management

- **High-Res Artwork**: Crisp 90x90px album art display in the track list.
- **"All Tracks" Master View**: Instant access to your entire collection.
- **Smart Drag & Drop**: Import folders or files directly from your OS.
- **Advanced Deletion**: Safe removal options with capability to delete from **Playlist**, **Library (DB)**, and **Disk** (permanently).
- **SQLite Architecture**: Zero-config, single-file database. No external servers required.

### 🎼 Advanced Audio Analysis

- **Camelot Key Detection**: Harmonic mixing compatible keys (1A-12B) calculated via Essentia.
- **BPM Precision**: Accurate tempo detection using industry-standard algorithms.
- **Energy Level**: 0-10 intensity rating based on spectral analysis.
- **Waveform Visualization**: Dual-deck style colored waveforms.

### 🔄 Professional Transcoding Workflow

- **Format Conversion**: Convert **FLAC** to **AIFF** (24-bit), **WAV**, or **MP3** (320kbps).
- **Metadata Clone**: **Lossless transfer of all tags** (Title, Artist, Album, Key, BPM) and **Album Artwork** during conversion.
- **CDJ Ready**: specifically optimized for compatibility with Pioneer CDJs (AIFF 24-bit).
- **Auto-Refresh**: Devices view updates automatically when transcoding finishes.

### 🎹 Usabilidad & Control

- **Custom Keyboard Shortcuts**: Fully configurable keybindings for playback, loading, and analysis.
- **Dual Deck Player**: Preview tracks A/B with independent controls.
- **Playlists**: Create, rename, analyze, and simple management.
- **Rekordbox Export**: Generate XML files compatible with Rekordbox.

---

## 🚀 Installation

### Prerequisites

- **Python 3.10+**
- **FFmpeg** (for transcoding)

### Quick Start (Linux/macOS)

```bash
# 1. Clone
git clone https://github.com/esfingex/tonemix.git
cd tonemix

# 2. Setup (Installs venv and dependencies)
./setup.sh

# 3. Run
./run.sh
```

### Manual Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 🎮 Controls (Default)

You can customize these in **View -> Preferences -> Shortcuts**.

| Action | Shortcut |
|--------|----------|
| **Play/Pause Deck A** | `Space` |
| **Play/Pause Deck B** | `Ctrl + Space` |
| **Load to Deck A** | `Ctrl + 1` |
| **Load to Deck B** | `Ctrl + 2` |
| **Delete Track(s)** | `Delete` |
| **Re-Analyze** | `Ctrl + R` |
| **Transcode** | `Ctrl + T` |

---

## 🛠️ Technology Stack

- **Core**: Python 3.10
- **UI**: PySide6 (Qt)
- **Audio Analysis**: Essentia & Librosa
- **Database**: SQLite + SQLAlchemy ORM
- **Metadata**: Mutagen
- **Transcoding**: FFmpeg

---

## 🛣️ Roadmap

### Phase 1: Core & Stability (✅ Completed)

- [x] SQLite Migration (Simplified Architecture)
- [x] Robust Metadata Preservation (FLAC -> AIFF)
- [x] High-Res Album Art
- [x] Keyboard Shortcuts System
- [x] Drag & Drop Import

### Phase 2: Enhanced Creative Tools (Planned)

- [ ] Cue Point Management
- [ ] Smart Playlists (Auto-filter by Key/BPM)
- [ ] Cloud Sync (Dropbox/GDrive backup)
- [ ] Stems Separation

---

## 🤝 Contributing

Contributions are welcome! Please check the `docs/` folder for developer guides.

## 📝 License

MIT License. Free for personal and professional use.
