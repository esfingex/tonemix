# ToneMix - UI Design Specification

## Based on Professional Reference Design

![Mixed In Key Pro Reference](/home/esfingex/.gemini/antigravity/brain/ca3c6443-efc3-4801-8abd-a12f70fd065e/uploaded_image_1767572591830.png)

## Layout Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│  [TONEMIX PRO] 🎵  My Collection | Pro | Tag Editor | Settings    [?] │
├───────┬────────────────────────────────────────────────────────────────┤
│       │  ┌──────────────────────────────────────────────────────────┐ │
│       │  │ DUAL DECK WAVEFORM VIEW (Mashup Mode)                   │ │
│ Play- │  │ ┌────────────────────┐  ┌────────────────────────────┐  │ │
│ lists │  │ │ DECK A             │  │ DECK B                     │  │ │
│       │  │ │ [▓▓▒▒░░▓▓▓▒▒░]     │  │ [░▒▒▓▓▓▒░░▓▓]              │  │ │
│ ├─All │  │ │ 7A│134 BPM│E:7│1:34│  │ 7A│123 BPM│E:6│2:06        │  │ │
│ ├─Ana │  │ │ [Change key][Stems]│  │ [Change key][Stems][Loop]  │  │ │
│ ├─Fav │  │ └────────────────────┘  └────────────────────────────┘  │ │
│ ├─Tra │  │ [Mashup Tools: Markers | DJ Mix | Idea Filter | 2/23]  │ │
│ └─DJ  │  └──────────────────────────────────────────────────────────┘ │
│       ├───────────────────────────────────────────────────────────────┤
│       │  TRACK LIBRARY TABLE                                         │
│       │  [Key ▼] [Tempo ▼] [Energy ▼] [Genres ▼] [Reset]            │
│       │  ┌────┬────────┬──────────────────┬────┬──────┬─────┬───────┐│
│       │  │Art │ Artist │ Title            │Key │Tempo │Enrgy│Rating ││
│       │  ├────┼────────┼──────────────────┼────┼──────┼─────┼───────┤│
│       │  │🎨  │Kolsch  │Cold Air          │7A  │ 128  │ 7   │⭐⭐⭐⭐⭐││
│       │  │🎨  │Eelke K │Transmission...   │7A  │ 124  │ 8   │⭐⭐⭐⭐ ││
│       │  │🎨  │Gregoré │Combustion n32    │1A  │ 124  │ 6   │⭐⭐⭐⭐ ││
│       │  └────┴────────┴──────────────────┴────┴──────┴─────┴───────┘│
└───────┴───────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Top Navigation Bar

**File**: `src/ui/widgets/top_navigation_bar.py`

**Elements**:

- Logo: "TONEMIX PRO" con icono musical
- Navigation tabs: `My Collection` | `Pro` | `Tag Editor` | `Settings`
- Help button: `[?]` (top-right corner)

**Styling**:

- Background: `#2a2a2a`
- Active tab: `#00d9ff` (cyan accent)
- Inactive tabs: `#808080`
- Height: 50px

---

### 2. Playlist Sidebar

**File**: `src/ui/widgets/playlist_sidebar.py`

**Structure** (basado en la imagen):

```
Playlists                          [+]
├─ 📁 All Music (2880)
├─ 📊 Analysis Queue (empty)
├─ ⭐ Favorite Mashups (4)
├─ 🎵 Trance Classics (234)
├─ 🎶 Melodic House (194)
├─ 🏠 Deep House (82)
└─ 🎧 DJ Mix
```

**Features**:

- QTreeWidget con iconos emoji
- Contadores de tracks entre paréntesis
- Botón `[+]` para crear nueva playlist
- Drag & drop: arrastrar tracks a playlists
- Context menu: New, Rename, Delete, Export

**Styling**:

- Width: 200px (collapsible)
- Background: `#1a1a1a`
- Selected item: `#3a3a3a`
- Border-right: `1px solid #2a2a2a`

---

### 3. Dual Deck Waveform Area

**File**: `src/ui/widgets/dual_deck_widget.py`

**Layout**: Dos decks lado a lado, cada uno con:

#### Deck Components

1. **Waveform Display**
   - Gradient rosa/morado con transparencia
   - Grid overlay con números (1, 2, 3, 4, 5, 6, 7, 8)
   - Playhead (línea vertical amarilla/naranja)
   - Height: ~150px

2. **Track Info Bar** (debajo del waveform):
   - Key badge: `7A` (con color de fondo Camelot)
   - BPM: `134 BPM`
   - Energy: `E:7`
   - Duration/Position: `1:34 / 6:09`

3. **Control Buttons**:
   - `[Change key]`: Transponer tonalidad
   - `[Stems]`: Separación de stems
   - `[Loop]`: Loop controls
   - `[Export]`: Exportar deck

**Waveform Rendering** (`waveform_widget.py`):

```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Background
    painter.fillRect(self.rect(), QColor(30, 30, 30))
    
    # Waveform gradient (rosa/morado)
    gradient = QLinearGradient(0, 0, 0, self.height())
    gradient.setColorAt(0, QColor(255, 100, 200, 180))    # Rosa top
    gradient.setColorAt(0.5, QColor(200, 100, 255, 200))  # Morado mid
    gradient.setColorAt(1, QColor(255, 100, 200, 180))    # Rosa bottom
    
    bar_width = self.width() / len(self.waveform_data)
    
    for i, amplitude in enumerate(self.waveform_data):
        x = i * bar_width
        bar_height = (amplitude / max_amplitude) * (self.height() / 2)
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        
        # Symmetric waveform (top and bottom)
        painter.drawRect(
            QRectF(x, self.height()/2 - bar_height, bar_width, bar_height * 2)
        )
    
    # Draw beat grid
    self.draw_beat_grid(painter)
    
    # Draw playhead
    playhead_x = (self.playhead_position / self.duration) * self.width()
    painter.setPen(QPen(QColor(255, 200, 0), 2))  # Amarillo/naranja
    painter.drawLine(playhead_x, 0, playhead_x, self.height())

def draw_beat_grid(self, painter):
    """Dibuja grid con números de beats"""
    painter.setPen(QPen(QColor(80, 80, 80), 1))
    
    # Asumiendo 4 beats por bar, 8 bars visibles
    num_markers = 8
    for i in range(num_markers + 1):
        x = (i / num_markers) * self.width()
        painter.drawLine(x, 0, x, self.height())
        
        # Número del marker
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(x + 5, 15, str(i + 1))
        painter.setPen(QPen(QColor(80, 80, 80), 1))
```

---

### 4. Mashup Tools Panel

**File**: `src/ui/widgets/mashup_tools_panel.py`

**Elements** (de izquierda a derecha):

1. **Markers button**: Crear markers de mezcla
2. **DJ Mix dropdown**: Tipo de mezcla (Mashup ideas, DJ Mix, etc.)
3. **Idea Filter dropdown**: Filtros de compatibilidad
4. **Progress indicator**: `2 / 23` (track actual / total)
5. **Sync button**: Sincronizar BPM entre decks
6. **Save mashup button**: Guardar proyecto

**Styling**:

- Background: `#252525`
- Height: 40px
- Buttons: `#3a3a3a` con hover `#4a4a4a`

---

### 5. Library Table

**File**: `src/ui/widgets/library_table_view.py`

#### Filter Bar (arriba de la tabla)

- Dropdowns: `[Key ▼]` `[Tempo ▼]` `[Energy ▼]` `[Genres ▼]`
- `[Reset]` button para limpiar filtros

#### Table Columns

| Column | Width | Type | Description |
|--------|-------|------|-------------|
| Cover Art | 60px | Image | Thumbnail del album (50x50px) |
| Artist | 150px | Text | Nombre del artista |
| Title | 250px | Text | Título del track |
| Key | 50px | Badge | Camelot key con color de fondo |
| Tempo | 70px | Number | BPM con decimales (ej: 128.00) |
| Standard | 60px | Text | Formato de tiempo (Dm, Cm, Am) |
| Energy | 50px | Number | Nivel 1-10 |
| Cue Points | 70px | Number | Número de cue points |
| Comment | 150px | Text | Comentarios del usuario |
| Rating | 80px | Stars | 1-5 estrellas |

#### Custom Delegates

**KeyDelegate** - Renderiza Key con color Camelot:

```python
class KeyDelegate(QStyledItemDelegate):
    """Renderiza Key con color de fondo Camelot"""
    
    CAMELOT_COLORS = {
        # Minor keys (A)
        '1A': QColor(255, 100, 100),   # Rojo
        '2A': QColor(255, 150, 100),   # Naranja
        '3A': QColor(255, 200, 100),   # Amarillo-naranja
        '4A': QColor(255, 250, 100),   # Amarillo
        '5A': QColor(200, 255, 100),   # Amarillo-verde
        '6A': QColor(150, 255, 100),   # Verde claro
        '7A': QColor(100, 255, 150),   # Verde
        '8A': QColor(100, 255, 200),   # Verde-cyan
        '9A': QColor(100, 250, 255),   # Cyan
        '10A': QColor(100, 200, 255),  # Cyan-azul
        '11A': QColor(100, 150, 255),  # Azul
        '12A': QColor(150, 100, 255),  # Morado
        
        # Major keys (B) - tonos más claros
        '1B': QColor(255, 130, 130),
        '2B': QColor(255, 170, 130),
        '3B': QColor(255, 210, 130),
        '4B': QColor(255, 255, 130),
        '5B': QColor(210, 255, 130),
        '6B': QColor(170, 255, 130),
        '7B': QColor(130, 255, 170),
        '8B': QColor(130, 255, 210),
        '9B': QColor(130, 250, 255),
        '10B': QColor(130, 210, 255),
        '11B': QColor(130, 170, 255),
        '12B': QColor(170, 130, 255),
    }
    
    def paint(self, painter, option, index):
        key = index.data()
        color = self.CAMELOT_COLORS.get(key, QColor(100, 100, 100))
        
        # Draw rounded rectangle background
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        
        rect = option.rect.adjusted(4, 4, -4, -4)
        painter.drawRoundedRect(rect, 4, 4)
        
        # Draw text
        painter.setPen(Qt.white if self.is_dark_color(color) else Qt.black)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, key)
    
    def is_dark_color(self, color):
        """Determina si el color es oscuro para elegir texto blanco/negro"""
        luminance = (0.299 * color.red() + 
                    0.587 * color.green() + 
                    0.114 * color.blue())
        return luminance < 128
```

**RatingDelegate** - Renderiza estrellas:

```python
class RatingDelegate(QStyledItemDelegate):
    """Renderiza rating con estrellas clickeables"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Cargar iconos de estrellas
        self.star_filled = QPixmap(":/icons/star_filled.png").scaled(16, 16)
        self.star_empty = QPixmap(":/icons/star_empty.png").scaled(16, 16)
    
    def paint(self, painter, option, index):
        rating = index.data() or 0  # 0-5
        
        # Draw background if selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        # Draw stars
        star_width = 16
        star_spacing = 2
        x_start = option.rect.x() + 5
        y = option.rect.y() + (option.rect.height() - 16) // 2
        
        for i in range(5):
            x = x_start + (i * (star_width + star_spacing))
            
            if i < rating:
                painter.drawPixmap(x, y, self.star_filled)
            else:
                painter.drawPixmap(x, y, self.star_empty)
    
    def editorEvent(self, event, model, option, index):
        """Permite cambiar rating con click"""
        if event.type() == QEvent.MouseButtonRelease:
            x = event.pos().x() - option.rect.x()
            star_width = 16
            star_spacing = 2
            
            # Calcular qué estrella se clickeó
            new_rating = min(5, max(0, int(x / (star_width + star_spacing)) + 1))
            model.setData(index, new_rating, Qt.EditRole)
            return True
        
        return super().editorEvent(event, model, option, index)
```

**CoverArtDelegate** - Renderiza thumbnails:

```python
class CoverArtDelegate(QStyledItemDelegate):
    """Renderiza cover art thumbnail"""
    
    def paint(self, painter, option, index):
        image_path = index.data()
        
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(
                50, 50, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # Center image in cell
            x = option.rect.x() + (option.rect.width() - pixmap.width()) // 2
            y = option.rect.y() + (option.rect.height() - pixmap.height()) // 2
            
            painter.drawPixmap(x, y, pixmap)
        else:
            # Default music icon
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(option.rect, Qt.AlignCenter, "🎵")
```

#### Table Features

**Context Menu**:

```python
def contextMenuEvent(self, event):
    menu = QMenu(self)
    
    # Actions
    analyze_action = menu.addAction("🔍 Analyze")
    reanalyze_action = menu.addAction("🔄 Re-analyze")
    menu.addSeparator()
    
    transcode_action = menu.addAction("🎵 Transcode to AIFF")
    menu.addSeparator()
    
    load_deck_a = menu.addAction("▶️ Load to Deck A")
    load_deck_b = menu.addAction("▶️ Load to Deck B")
    menu.addSeparator()
    
    add_playlist = menu.addAction("➕ Add to Playlist...")
    export_rekordbox = menu.addAction("📤 Export to Rekordbox")
    menu.addSeparator()
    
    delete_action = menu.addAction("🗑️ Delete from Library")
    
    # Execute
    action = menu.exec_(self.viewport().mapToGlobal(event.pos()))
    
    if action == analyze_action:
        self.analyze_selected_tracks()
    elif action == load_deck_a:
        self.load_to_deck('A')
    # ... etc
```

**Double-click behavior**:

```python
def mouseDoubleClickEvent(self, event):
    """Double-click carga track en deck disponible"""
    index = self.indexAt(event.pos())
    if index.isValid():
        track = self.model().get_track(index.row())
        
        # Load to first available deck
        if not self.deck_a_widget.has_track():
            self.deck_a_widget.load_track(track)
        elif not self.deck_b_widget.has_track():
            self.deck_b_widget.load_track(track)
        else:
            # Both decks occupied, ask user
            self.show_deck_selection_dialog(track)
```

---

## Color Palette

### Dark Theme Base

```css
--background-primary: #1a1a1a
--background-secondary: #2a2a2a
--background-tertiary: #252525
--border-color: #3a3a3a
--text-primary: #e0e0e0
--text-secondary: #b0b0b0
--accent-cyan: #00d9ff
--accent-yellow: #ffc800
```

### Waveform Colors

```css
--waveform-gradient-start: rgba(255, 100, 200, 0.7)  /* Rosa */
--waveform-gradient-mid: rgba(200, 100, 255, 0.8)    /* Morado */
--waveform-gradient-end: rgba(255, 100, 200, 0.7)    /* Rosa */
--playhead-color: #ffc800                             /* Amarillo */
--grid-color: #505050                                 /* Gris oscuro */
```

### Energy Level Colors

```css
--energy-low: #4caf50      /* Verde */
--energy-mid: #ffeb3b      /* Amarillo */
--energy-high: #f44336     /* Rojo */
```

---

## Responsive Behavior

### Window Sizes

- **Minimum**: 1024x600
- **Recommended**: 1280x720
- **Optimal**: 1920x1080

### Collapsible Elements

- Playlist sidebar: Toggle con `Ctrl+P`
- Dual deck area: Toggle con `Ctrl+D` (muestra solo tabla)
- Filter bar: Auto-hide cuando no está en uso

### Scaling

- Waveforms escalan horizontalmente con ventana
- Tabla usa scroll vertical para muchos tracks
- Sidebar tiene width fijo (200px) pero collapsible

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause deck activo |
| `Ctrl+A` | Analyze selected tracks |
| `Ctrl+T` | Transcode selected |
| `Ctrl+E` | Export to Rekordbox |
| `Ctrl+F` | Focus search/filter |
| `Ctrl+P` | Toggle playlist sidebar |
| `Ctrl+D` | Toggle dual deck view |
| `1-5` | Set rating para track seleccionado |
| `Delete` | Remove from library |
| `F2` | Edit track metadata |

---

## Implementation Priority

### Phase 1 (MVP)

1. ✅ Main window layout
2. ✅ Library table con columnas básicas
3. ✅ Single waveform widget
4. ✅ Playlist sidebar básico

### Phase 2 (Enhanced)

1. ⏳ Dual deck layout
2. ⏳ Custom delegates (Key, Rating, Cover Art)
3. ⏳ Filter bar
4. ⏳ Context menus

### Phase 3 (Pro Features)

1. ⏳ Mashup tools panel
2. ⏳ Beat grid overlay
3. ⏳ Stems integration
4. ⏳ Advanced keyboard shortcuts
