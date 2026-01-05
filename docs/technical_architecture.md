# ToneMix - Professional Music Analysis Software

## Phase 1: Core Analysis Engine & UI Foundation

Diseño e implementación de un software profesional de análisis musical con capacidades MIR (Music Information Retrieval), interfaz gráfica moderna con PySide6, y exportación a Rekordbox.

## User Review Required

> [!IMPORTANT]
> **Decisiones de Arquitectura Clave**
>
> - **PostgreSQL como Base de Datos**: Se utilizará PostgreSQL para almacenar la librería musical, permitiendo integración futura con el ecosistema Solaria.
> - **Waveform Rendering Strategy**: Los waveforms se renderizarán usando downsampling a ~2000 puntos para mantener la UI responsiva, incluso con tracks de 7+ minutos.
> - **Threading Model**: Se usará `QThread` para análisis de audio y `multiprocessing` para batch processing de múltiples archivos.
> - **Camelot Wheel Mapping**: Las tonalidades se almacenarán en formato Camelot (1A-12B) para compatibilidad con DJ workflows.

> [!WARNING]
> **Dependencias Externas Requeridas**
>
> - FFmpeg debe estar instalado en el sistema para transcoding
> - PostgreSQL server debe estar corriendo
> - Las librerías de audio (Essentia, Librosa) requieren compilación nativa

## Proposed Changes

### Project Structure

```
tonemix/
├── src/
│   ├── core/
│   │   ├── analyzer.py          # Audio analysis engine
│   │   ├── transcoder.py        # FFmpeg wrapper
│   │   └── audio_processor.py   # Audio loading
│   ├── database/
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── connection.py        # DB connection
│   │   └── repository.py        # CRUD operations
│   ├── ui/
│   │   ├── main_window.py       # Main window
│   │   └── widgets/
│   │       ├── waveform_widget.py
│   │       ├── library_view.py
│   │       └── drop_zone.py
│   ├── export/
│   │   └── rekordbox_exporter.py
│   └── utils/
│       ├── camelot.py
│       └── config.py
├── requirements.txt
├── config.yaml
└── main.py
```

---

### Core Analysis Module

#### [NEW] [analyzer.py](file:///home/esfingex/workspace/ToneMix/src/core/analyzer.py)

**Pipeline de análisis musical usando Essentia y Librosa**

Funcionalidades:

- `analyze_track(audio_path: str) -> TrackAnalysis`: Orquesta el análisis completo
- `extract_key(audio, sr) -> str`: Extrae tonalidad en formato Camelot usando Essentia KeyExtractor
- `extract_bpm(audio, sr) -> float`: Detecta BPM con Essentia RhythmExtractor
- `calculate_energy(audio, sr) -> float`: Calcula energía (0-10) basado en RMS + Spectral Centroid

Implementación técnica:

```python
# Essentia KeyExtractor con perfil electrónico
key_extractor = essentia.standard.KeyExtractor(profileType='electronic')

# Energy: weighted combination
rms_energy = np.sqrt(np.mean(audio**2))
spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
energy = normalize(rms_energy * 0.6 + spectral_centroid_mean * 0.4, 0, 10)
```

#### [NEW] [transcoder.py](file:///home/esfingex/workspace/ToneMix/src/core/transcoder.py)

**Conversión FLAC a AIFF 24-bit con preservación de metadatos**

Funcionalidades:

- `transcode_to_aiff(input_path, output_path) -> bool`
- `inject_id3_tags(aiff_path, tags) -> bool`: Inyecta Initial Key con Mutagen

FFmpeg command:

```bash
ffmpeg -i input.flac -acodec pcm_s24be -f aiff -map_metadata 0 output.aiff
```

#### [NEW] [audio_processor.py](file:///home/esfingex/workspace/ToneMix/src/core/audio_processor.py)

**Carga y preprocesamiento de audio**

Funcionalidades:

- `load_audio(path) -> Tuple[np.ndarray, int]`: Carga con Librosa, resample a 44.1kHz
- `downsample_waveform(audio, target_points=2000) -> np.ndarray`: Reduce datos para rendering

---

### Database Layer

#### [NEW] [models.py](file:///home/esfingex/workspace/ToneMix/src/database/models.py)

**Esquema SQLAlchemy para librería musical**

```python
class Track(Base):
    __tablename__ = 'tracks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255))
    album = Column(String(255))
    
    # Analysis results
    key_camelot = Column(String(3))      # "8A", "12B"
    key_musical = Column(String(10))     # "C major", "Am"
    bpm = Column(Float)
    energy_level = Column(Float)         # 0-10 scale
    
    # File info
    file_path = Column(String(512), unique=True, nullable=False)
    file_format = Column(String(10))
    duration_seconds = Column(Float)
    
    # Waveform (binary)
    waveform_data = Column(LargeBinary)  # Downsampled ~2000 points
    
    # Transcoding
    transcoded_path = Column(String(512))
    is_transcoded = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime)
```

#### [NEW] [connection.py](file:///home/esfingex/workspace/ToneMix/src/database/connection.py)

**Gestión de conexiones PostgreSQL**

Funcionalidades:

- `get_engine() -> Engine`: Singleton para SQLAlchemy engine
- `get_session() -> Session`: Context manager para sesiones
- `init_database()`: Crea todas las tablas

#### [NEW] [repository.py](file:///home/esfingex/workspace/ToneMix/src/database/repository.py)

**CRUD operations para tracks**

Funcionalidades:

- `create_track(track_data: dict) -> Track`
- `get_track_by_path(path: str) -> Optional[Track]`
- `update_track(track_id: int, updates: dict) -> Track`
- `get_all_tracks(filters: dict = None) -> List[Track]`

---

### UI Components (PySide6)

#### [NEW] [main_window.py](file:///home/esfingex/workspace/ToneMix/src/ui/main_window.py)

**Ventana principal con layout Rekordbox-style**

Layout:

```
┌─────────────────────────────────────────┐
│  [Drop Zone - Drag files here]         │
├─────────────────────────────────────────┤
│  Library View                           │
│  Title │ Artist │ Key │ BPM │ Energy   │
├─────────────────────────────────────────┤
│  Waveform Widget                        │
│  [████▌  ▐███  ▐██████▌]  [▶]          │
└─────────────────────────────────────────┘
```

Threading:

- `AnalysisWorker(QThread)`: Worker para análisis sin bloquear UI
- Signals: `analysis_complete`, `progress_update`, `error_occurred`

#### [NEW] [waveform_widget.py](file:///home/esfingex/workspace/ToneMix/src/ui/widgets/waveform_widget.py)

**Visualización de forma de onda con QPainter**

Características:

- Rendering con `QPainter`: líneas verticales por amplitud
- Downsampling: ~2000 puntos pre-calculados desde DB
- Color coding: verde (low) → amarillo (mid) → rojo (high)
- Playhead: línea vertical sincronizada con `QMediaPlayer`
- Interacción: click para seek, scroll para zoom

Algoritmo:

```python
def paintEvent(self, event):
    painter = QPainter(self)
    bar_width = self.width() / len(self.waveform_data)
    
    for i, amplitude in enumerate(self.waveform_data):
        x = i * bar_width
        bar_height = (amplitude / max_amplitude) * (height / 2)
        color = self.get_energy_color(amplitude)
        painter.setPen(color)
        painter.drawLine(x, height/2 - bar_height, 
                        x, height/2 + bar_height)
```

#### [NEW] [library_view.py](file:///home/esfingex/workspace/ToneMix/src/ui/widgets/library_view.py)

**QTableView personalizado para librería**

Funcionalidades:

- Custom delegates: Key con color Camelot, BPM con decimales
- Sorting por columna
- Filtrado en tiempo real
- Context menu: Analyze, Transcode, Export, Delete
- Double-click carga waveform

#### [NEW] [drop_zone.py](file:///home/esfingex/workspace/ToneMix/src/ui/widgets/drop_zone.py)

**Widget drag & drop para archivos/carpetas**

Funcionalidades:

- Acepta: `.flac`, `.aiff`, `.wav`, `.mp3`, `.m4a`
- Escaneo recursivo de carpetas
- Validación de formatos
- Emit signal con lista de paths válidos

---

### Rekordbox Integration

#### [NEW] [rekordbox_exporter.py](file:///home/esfingex/workspace/ToneMix/src/export/rekordbox_exporter.py)

**Generación de rekordbox.xml compatible**

Funcionalidades:

- `export_library(tracks: List[Track], output_path: str) -> bool`
- `generate_xml_track_node(track: Track) -> ET.Element`
- Path mapping para archivos transcodificados

Estructura XML:

```xml
<DJ_PLAYLISTS Version="1.0.0">
  <PRODUCT Name="ToneMix" Version="1.0.0"/>
  <COLLECTION Entries="100">
    <TRACK TrackID="1" Name="Title" Artist="Artist"
           Tonality="8A" AverageBpm="128.00" 
           Location="file://localhost/path/file.aiff"/>
  </COLLECTION>
</DJ_PLAYLISTS>
```

---

### Utilities

#### [NEW] [camelot.py](file:///home/esfingex/workspace/ToneMix/src/utils/camelot.py)

**Conversión notación musical ↔ Camelot Wheel**

```python
CAMELOT_MAP = {
    'C major': '8B', 'A minor': '8A',
    'G major': '9B', 'E minor': '9A',
    'D major': '10B', 'B minor': '10A',
    # ... complete mapping
}
```

#### [NEW] [config.py](file:///home/esfingex/workspace/ToneMix/src/utils/config.py)

**Carga configuración desde config.yaml**

---

### Configuration Files

#### [NEW] [requirements.txt](file:///home/esfingex/workspace/ToneMix/requirements.txt)

```txt
essentia==2.1b6.dev1110
librosa==0.10.1
PySide6==6.6.1
SQLAlchemy==2.0.23
psycopg2-binary==2.9.9
mutagen==1.47.0
pyrekordbox==0.1.8
PyYAML==6.0.1
pytest==7.4.3
```

#### [NEW] [config.yaml](file:///home/esfingex/workspace/ToneMix/config.yaml)

```yaml
database:
  host: localhost
  port: 5432
  name: tonemix
  user: postgres

audio:
  sample_rate: 44100
  waveform_points: 2000
  supported_formats: [flac, aiff, wav, mp3, m4a]

transcoding:
  output_format: aiff
  bit_depth: 24
```

#### [NEW] [main.py](file:///home/esfingex/workspace/ToneMix/main.py)

**Entry point de la aplicación**

```python
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.database.connection import init_database

def main():
    init_database()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

---

## Verification Plan

### Automated Tests

```bash
# Unit tests
pytest tests/test_analyzer.py -v      # Key, BPM, Energy accuracy
pytest tests/test_transcoder.py -v    # FLAC→AIFF conversion
pytest tests/test_waveform.py -v      # Widget rendering

# Integration tests
pytest tests/test_database.py -v      # CRUD operations
pytest tests/test_rekordbox_export.py # XML validation
```

### Manual Verification

1. **UI Testing**: Drag & drop carpeta → Analyze → Verificar tabla poblada
2. **Waveform**: Double-click track → Verificar rendering fluido
3. **Transcoding**: Click derecho → Transcode → Validar AIFF creado
4. **Export**: Seleccionar tracks → Export to Rekordbox → Validar XML

### Performance Criteria

- Waveform rendering: < 100ms para tracks de 7+ minutos
- UI responsiva durante análisis (threading funciona)
- Batch analysis usa múltiples cores
- Memoria < 2GB durante análisis de 50+ tracks
