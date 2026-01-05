"""
Deck widget combining Waveform and Audio Player
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal
import logging

from src.ui.widgets.waveform_widget import WaveformWidget
from src.ui.widgets.audio_player import AudioPlayer
from src.database.models import Track

logger = logging.getLogger(__name__)


class DeckWidget(QWidget):
    """
    DJ Deck widget containing waveform, player, and track info
    """
    track_dropped = Signal(int) # track_id
    
    def __init__(self, deck_id: str, parent=None):
        super().__init__(parent)
        self.deck_id = deck_id # "A" or "B"
        self.current_track = None
        
        self.setAcceptDrops(True)
        self._init_ui()
        
    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasFormat("application/x-tonemix-track-ids"):
            event.acceptProposedAction()
            self.setStyleSheet("border: 2px solid #00E5FF;") # Highlight
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self.setStyleSheet("") # Clear highlight/border
            
    def dropEvent(self, event):
        """Handle drop event"""
        self.setStyleSheet("") # Clear highlight
        
        if event.mimeData().hasFormat("application/x-tonemix-track-ids"):
            import json
            data = event.mimeData().data("application/x-tonemix-track-ids").data()
            track_ids = json.loads(data)
            
            if track_ids:
                # Load first track
                track_id = track_ids[0]
                
                # Signal parent or handle loading directly?
                # Deck doesn't have reference to repository easily...
                # Ideally emit signal "track_dropped" and let MainWindow handle loading
                self.track_dropped.emit(track_id)
                
            event.acceptProposedAction()
        
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Top Bar: Deck Label + Title (No more Key/BPM here)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(5, 5, 5, 0)
        
        # Deck Label
        self.deck_label = QLabel(f"DECK {self.deck_id}")
        self.deck_label.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {'#00E5FF' if self.deck_id == 'A' else '#FF4081'};"
        )
        top_bar.addWidget(self.deck_label)
        
        # Track Title (Centered or Left)
        self.title_label = QLabel("No Track Loaded")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        self.title_label.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(self.title_label, 1) # Expand
        
        layout.addLayout(top_bar)
        
        # 2. Main Visual Area: Artwork (Left) + Waveform (Right)
        visuals_layout = QHBoxLayout()
        visuals_layout.setContentsMargins(0, 0, 0, 0)
        visuals_layout.setSpacing(0)
        
        # Artwork
        self.artwork_label = QLabel()
        self.artwork_label.setFixedSize(80, 80) # Slightly larger for better visibility
        self.artwork_label.setStyleSheet("background-color: #222; border-right: 1px solid #444;")
        self.artwork_label.setScaledContents(True)
        self.artwork_label.setAlignment(Qt.AlignCenter)
        self.artwork_label.setText("🎵")
        visuals_layout.addWidget(self.artwork_label)
        
        # Waveform
        self.waveform = WaveformWidget()
        self.waveform.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.waveform.setMinimumHeight(80) # Match artwork height approx
        visuals_layout.addWidget(self.waveform)
        
        layout.addLayout(visuals_layout, 1) # Expand visuals
        
        # 3. Player Controls (Bottom)
        self.player = AudioPlayer()
        layout.addWidget(self.player)
        
        # Connect signals
        self.player.position_changed.connect(self._on_player_position_changed)
        
        # Add border
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        
    
    def setFrameStyle(self, style):
        # Helper for QFrame-like behavior if inheriting QWidget
        pass

    def load_track(self, track: Track):
        """Load track into deck"""
        self.current_track = track
        
        # Update labels
        self.title_label.setText(f"{track.title}")
        
        # NO Key/BPM info label anymore
        # The user wanted ONLY the title above the wave
        
        # Load audio into player
        if track.file_path:
            self.player.load_track(track.file_path)
            
            # Load artwork
            from src.core.audio_processor import AudioProcessor
            from PySide6.QtGui import QPixmap, QImage
            
            processor = AudioProcessor()
            artwork_data = processor.get_artwork(track.file_path)
            
            if artwork_data:
                image = QImage.fromData(artwork_data)
                self.artwork_label.setPixmap(QPixmap.fromImage(image))
            else:
                self.artwork_label.clear()
                self.artwork_label.setText("🎵") # Placeholder
                self.artwork_label.setAlignment(Qt.AlignCenter)
        
        # Load waveform
        if track.waveform_data:
            # Use AudioProcessor to deserialize (handles pickle vs raw)
            from src.core.audio_processor import AudioProcessor
            processor = AudioProcessor()
            waveform = processor.bytes_to_waveform(track.waveform_data)
                
            self.waveform.set_waveform(
                waveform, 
                track.duration_seconds,
                key=track.key_camelot,
                bpm=track.bpm,
                energy=track.energy_level
            )
            
            # Connect seek signal if not already connected (disconnect first to be safe)
            try:
                self.waveform.seek_requested.disconnect()
            except:
                pass
            self.waveform.seek_requested.connect(self._on_waveform_seek)
            
        else:
            # Clear waveform if not analyzed
            self.waveform.set_waveform(np.array([]))
            
    def _on_waveform_seek(self, position: float):
        """Handle seek request from waveform"""
        if self.current_track and self.current_track.duration_seconds > 0:
            ms = int(position * self.current_track.duration_seconds * 1000)
            self.player.set_position(ms)

    def _on_player_position_changed(self, ms: int):
        """Update waveform playhead"""
        if self.current_track and self.current_track.duration_seconds > 0:
            position = (ms / 1000) / self.current_track.duration_seconds
            self.waveform.set_playhead_position(position)
