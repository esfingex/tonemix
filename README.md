# 🎵 ToneMix Pro

**Professional Music Analysis Software for DJs and Producers**

ToneMix is an open-source music analysis tool inspired by industry standards, designed for professional DJs and music producers. It provides advanced Music Information Retrieval (MIR) capabilities with a modern, intuitive interface.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)

## ✨ Features

### 🎼 Advanced Audio Analysis

- **Key Detection**: Accurate musical key detection in Camelot Wheel format (1A-12B)
- **BPM Detection**: Precise tempo analysis using Essentia's RhythmExtractor
- **Energy Level**: Calculated energy rating (0-10) based on RMS and Spectral Centroid
- **Waveform Visualization**: Beautiful gradient waveforms with beat grid overlay

### 🎚️ Professional DJ Tools

- **Dual Deck Interface**: Side-by-side waveform comparison for mashup creation
- **Harmonic Mixing**: Camelot Wheel color-coding for compatible key matching
- **BPM Sync**: Automatic tempo synchronization between tracks
- **Mashup Tools**: Markers, idea filters, and project saving

### 🔄 Format Support

- **Audio Formats**: FLAC, AIFF, WAV, MP3, M4A
- **Transcoding**: High-quality FLAC to AIFF 24-bit conversion
- **Metadata Preservation**: Maintains ID3 tags during transcoding
- **Rekordbox Export**: Generate compatible XML for Rekordbox import

### 📊 Library Management

- **PostgreSQL Database**: Robust storage for large music libraries
- **Smart Playlists**: Filter by key, BPM, energy, and genre
- **Cover Art**: Automatic album artwork display
- **Rating System**: 5-star rating with visual feedback

## 🚀 Installation

### Prerequisites

Before installing ToneMix, ensure you have the following:

#### Required

- **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
- **FFmpeg**: Required for audio transcoding (FLAC → AIFF)

  ```bash
  # Ubuntu/Debian
  sudo apt install ffmpeg
  
  # macOS
  brew install ffmpeg
  ```

#### Optional

- **Essentia**: For advanced analysis (pip install essentia)
- **PostgreSQL**: Optional, ToneMix uses SQLite by default.

### Quick Setup

Use the automated setup script:

```bash
# Clone the repository
git clone https://github.com/esfingex/tonemix.git
cd tonemix

# Run setup script
./setup.sh

# Run ToneMix
./run.sh
```

### Manual Setup

If you prefer manual installation:

1. **Clone the repository**

   ```bash
   git clone https://github.com/esfingex/tonemix.git
   cd tonemix
   ```

2. **Create virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create PostgreSQL database**

   ```bash
   # Switch to postgres user
   sudo -u postgres psql
   
   # In PostgreSQL prompt:
   CREATE DATABASE tonemix;
   CREATE USER tonemix_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE tonemix TO tonemix_user;
   \q
   ```

5. **Configure environment**

   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your database credentials
   nano .env
   ```

   Update these values in `.env`:

   ```env
   DB_PASSWORD=your_password
   ```

6. **Run ToneMix**

   ```bash
   python main.py
   ```

### Verifying Installation

When you run ToneMix for the first time, you should see:

```
🎵 ToneMix Pro v0.1.0
============================================================
📋 Configuration:
  Database: localhost:5432/tonemix
  ✅ Essentia available
  ✅ FFmpeg available
✅ ToneMix Pro is ready!
```

If you see warnings about missing components:

- **Essentia not installed**: `pip install essentia` (in venv)
- **FFmpeg not found**: Install using instructions above
- **Database error**: Check PostgreSQL is running and credentials are correct

## 🎨 Screenshots

*Coming soon...*

## 🛠️ Technology Stack

- **Audio Analysis**: Essentia, Librosa
- **UI Framework**: PySide6 (Qt for Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Transcoding**: FFmpeg
- **Metadata**: Mutagen
- **Rekordbox Integration**: pyrekordbox

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [User Manual](docs/user_manual.md)
- [Developer Guide](docs/developer_guide.md)
- [API Reference](docs/api_reference.md)

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black src/

# Lint
flake8 src/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by professional DJ software aesthetics
- Built with [Essentia](https://essentia.upf.edu/) for audio analysis
- UI design influenced by professional DJ software aesthetics

## 🔧 Troubleshooting

### Common Installation Issues

**1. Essentia Version Not Found**
If you see an error like `No matching distribution found for essentia==...`:

- Edit `requirements.txt` and change the version to just `essentia` (to get the latest) or check available versions on PyPI.
- Alternatively, install slightly different version: `pip install essentia==2.1b6.dev1389`

**2. Database Connection Failed**

- Ensure PostgreSQL service is running: `sudo systemctl status postgresql`
- Verify credentials in `.env` file match what you set up in PostgreSQL.

**3. Audio Analysis Fails**

- Ensure FFmpeg is installed: `ffmpeg -version`
- Check log output for specific error messages.

## 🗺️ Roadmap

### Phase 1 ✅ COMPLETED

- [x] Project structure and architecture
- [x] Core audio analysis engine (Essentia + Librosa)
- [x] Database models and repository (PostgreSQL + SQLAlchemy)
- [x] Complete UI with waveform visualization
- [x] Rekordbox XML export
- [x] Batch file analysis
- [x] FLAC to AIFF transcoding

### Phase 2 (In Progress)

- [ ] Dual deck interface for mashup creation
- [ ] Mashup tools and markers
- [ ] Advanced filtering and search
- [ ] Playlist management
- [ ] Keyboard shortcuts
- [ ] Performance optimizations

### Phase 3 (Planned)

- [ ] Stems separation integration
- [ ] Cloud sync capabilities
- [ ] Mobile companion app
- [ ] Plugin system for extensibility
- [ ] VST/AU plugin support

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/esfingex/tonemix/issues)
- **Discussions**: [GitHub Discussions](https://github.com/esfingex/tonemix/discussions)
- **Email**: <support@tonemix.dev>

## ⭐ Star History

If you find ToneMix useful, please consider giving it a star! ⭐

---

**Made with ❤️ by the ToneMix community**
