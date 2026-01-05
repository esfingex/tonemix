# 🎵 ToneMix Pro

**Professional Music Analysis Software for DJs and Producers**

ToneMix is an open-source music analysis tool inspired by Mixed In Key, designed for professional DJs and music producers. It provides advanced Music Information Retrieval (MIR) capabilities with a modern, intuitive interface.

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

- Python 3.10 or higher
- PostgreSQL 12+
- FFmpeg (for transcoding)

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/tonemix.git
cd tonemix
```

1. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

1. **Configure database**

```bash
# Create PostgreSQL database
createdb tonemix

# Copy environment template
cp .env.example .env

# Edit .env and set your database password
nano .env
```

1. **Run ToneMix**

```bash
python main.py
```

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

- Inspired by [Mixed In Key](https://mixedinkey.com/)
- Built with [Essentia](https://essentia.upf.edu/) for audio analysis
- UI design influenced by professional DJ software aesthetics

## 🗺️ Roadmap

### Phase 1 (Current)

- [x] Project structure and architecture
- [ ] Core audio analysis engine
- [ ] Database models and repository
- [ ] Basic UI with waveform visualization
- [ ] Rekordbox XML export

### Phase 2

- [ ] Dual deck interface
- [ ] Mashup tools and markers
- [ ] Advanced filtering and search
- [ ] Batch analysis

### Phase 3

- [ ] Stems separation integration
- [ ] Cloud sync capabilities
- [ ] Mobile companion app
- [ ] Plugin system for extensibility

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/tonemix/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/tonemix/discussions)
- **Email**: <support@tonemix.dev>

## ⭐ Star History

If you find ToneMix useful, please consider giving it a star! ⭐

---

**Made with ❤️ by the ToneMix community**
