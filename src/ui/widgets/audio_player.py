"""
Simple audio player widget
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLabel
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import logging

logger = logging.getLogger(__name__)


class AudioPlayer(QWidget):
    """Simple audio player widget"""
    
    position_changed = Signal(int)  # milliseconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # UI
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Play/Pause button
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(40, 30)
        self.play_button.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_button)
        
        # Position label
        self.position_label = QLabel("0:00")
        self.position_label.setFixedWidth(50)
        layout.addWidget(self.position_label)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setEnabled(False)
        self.seek_slider.sliderMoved.connect(self._seek)
        layout.addWidget(self.seek_slider)
        
        # Duration label
        self.duration_label = QLabel("0:00")
        self.duration_label.setFixedWidth(50)
        layout.addWidget(self.duration_label)
        
        # Volume control
        layout.addSpacing(10)
        self.volume_label = QLabel("Vol")
        layout.addWidget(self.volume_label)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.audio_output.setVolume(0.7)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self.volume_slider)
        
        # Connect signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        
    def load_track(self, file_path: str):
        """Load audio file"""
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.seek_slider.setEnabled(True)
        logger.info(f"Loaded audio: {file_path}")
        
    def _toggle_play(self):
        """Toggle play/pause"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
            
    def toggle_playback(self):
        """Public method to toggle playback"""
        self._toggle_play()
        
    def set_position(self, ms: int):
        """Set position in milliseconds"""
        self.player.setPosition(ms)

    def _seek(self, position):
        """Seek to position"""
        self.player.setPosition(position)
    
    def _on_position_changed(self, position):
        """Update position"""
        self.seek_slider.setValue(position)
        self.position_label.setText(self._format_time(position))
        self.position_changed.emit(position)
    
    def _on_duration_changed(self, duration):
        """Update duration"""
        self.seek_slider.setMaximum(duration)
        self.duration_label.setText(self._format_time(duration))
    
    def _on_state_changed(self, state):
        """Update play button"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("⏸")
        else:
            self.play_button.setText("▶")
            
    def _on_volume_changed(self, value):
        """Update volume"""
        self.audio_output.setVolume(value / 100.0)
    
    def _format_time(self, ms):
        """Format milliseconds to MM:SS"""
        seconds = ms // 1000
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    
    def stop(self):
        """Stop playback"""
        self.player.stop()
