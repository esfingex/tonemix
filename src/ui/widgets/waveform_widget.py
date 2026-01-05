"""
Waveform visualization widget
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPointF, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush
import numpy as np
import logging

logger = logging.getLogger(__name__)


class WaveformWidget(QWidget):
    """Custom widget for waveform visualization"""
    
    # Signals
    position_clicked = Signal(float)  # Emits position (0.0 - 1.0)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.waveform_data = None
        self.playhead_position = 0.0  # 0.0 to 1.0
        self.duration = 0.0
        
        # Track metadata for overlays
        self.track_key = None
        self.track_bpm = None
        self.track_artwork = None
        
        # Preferences
        self.preferences = {
            'color_scheme': 0,  # 0=Rekordbox, 1=RGB, 2=Mono Blue, etc.
            'show_artwork': True,
            'show_key': False,
            'show_bpm': False,
            'show_beat_grid': False,
            'intensity': 1.0
        }
        
        # Colors
        self.bg_color = QColor(42, 42, 42)
        self.grid_color = QColor(80, 80, 80)
        self.playhead_color = QColor(255, 200, 0)
        
        # Default gradient colors (will be updated by color scheme)
        self._update_color_scheme()
        
        # Settings
        self.setMinimumHeight(120)
        self.setMouseTracking(True)
    
    def set_preferences(self, prefs):
        """Set waveform preferences"""
        self.preferences.update(prefs)
        self._update_color_scheme()
        self.update()
    
    def _update_color_scheme(self):
        """Update colors based on color scheme"""
        scheme = self.preferences.get('color_scheme', 0)
        intensity = self.preferences.get('intensity', 1.0)
        
        if scheme == 0:  # Rekordbox (RGB Spectrum)
            self.gradient_start = QColor(int(100 * intensity), int(100 * intensity), int(255 * intensity), 180)
            self.gradient_mid = QColor(int(255 * intensity), int(100 * intensity), int(200 * intensity), 200)
            self.gradient_end = QColor(int(255 * intensity), int(100 * intensity), int(100 * intensity), 180)
        elif scheme == 1:  # RGB Spectrum
            self.gradient_start = QColor(int(255 * intensity), 0, 0, 180)
            self.gradient_mid = QColor(0, int(255 * intensity), 0, 200)
            self.gradient_end = QColor(0, 0, int(255 * intensity), 180)
        elif scheme == 2:  # Monochrome Blue
            self.gradient_start = QColor(int(100 * intensity), int(150 * intensity), int(255 * intensity), 180)
            self.gradient_mid = QColor(int(100 * intensity), int(150 * intensity), int(255 * intensity), 200)
            self.gradient_end = QColor(int(100 * intensity), int(150 * intensity), int(255 * intensity), 180)
        elif scheme == 3:  # Monochrome Green
            self.gradient_start = QColor(int(100 * intensity), int(255 * intensity), int(100 * intensity), 180)
            self.gradient_mid = QColor(int(100 * intensity), int(255 * intensity), int(100 * intensity), 200)
            self.gradient_end = QColor(int(100 * intensity), int(255 * intensity), int(100 * intensity), 180)
        elif scheme == 4:  # Monochrome Orange
            self.gradient_start = QColor(int(255 * intensity), int(150 * intensity), int(50 * intensity), 180)
            self.gradient_mid = QColor(int(255 * intensity), int(150 * intensity), int(50 * intensity), 200)
            self.gradient_end = QColor(int(255 * intensity), int(150 * intensity), int(50 * intensity), 180)
    
    def set_waveform(self, waveform_data: np.ndarray, duration: float = 0.0, key: str = None, bpm: float = None, energy: int = None):
        """
        Set waveform data
        
        Args:
            waveform_data: Numpy array of waveform amplitudes
            duration: Duration in seconds
            key: Track key (e.g. "4A")
            bpm: Track BPM
            energy: Track energy
        """
        self.waveform_data = waveform_data
        self.duration = duration
        self.track_key = key
        self.track_bpm = bpm
        self.track_energy = energy
        self.playhead_position = 0.0
        self.update()
    
    def set_playhead_position(self, position: float):
        """
        Set playhead position
        
        Args:
            position: Position from 0.0 to 1.0
        """
        self.playhead_position = max(0.0, min(1.0, position))
        self.update()
    
    def paintEvent(self, event):
        """Paint the waveform"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Draw waveform if data available
        if self.waveform_data is not None and len(self.waveform_data) > 0:
            self._draw_waveform(painter)
            if self.preferences.get('show_beat_grid', False):
                self._draw_beat_grid(painter)
            self._draw_overlays(painter)
        else:
            # Draw placeholder text
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No waveform loaded")
        
        # Draw playhead
        self._draw_playhead(painter)

    
    def _draw_waveform(self, painter: QPainter):
        """Draw the waveform with spectral colors (Rekordbox-style)"""
        width = self.width()
        height = self.height()
        
        if len(self.waveform_data) == 0:
            return
        
        # Check if we have spectral data (dict) or simple waveform (array)
        is_spectral = isinstance(self.waveform_data, dict)
        
        if is_spectral:
            self._draw_spectral_waveform(painter, width, height)
        else:
            self._draw_simple_waveform(painter, width, height)
    
    def _draw_spectral_waveform(self, painter: QPainter, width: int, height: int):
        """Draw spectral waveform with frequency-based colors"""
        low_band = self.waveform_data.get('low', [])
        mid_band = self.waveform_data.get('mid', [])
        high_band = self.waveform_data.get('high', [])
        
        if len(low_band) == 0:
            return
        
        # Calculate bar width
        bar_width = max(1, width / len(low_band))
        y_center = height / 2
        
        # Get intensity multiplier
        intensity = self.preferences.get('intensity', 1.0)
        
        # Rekordbox-style colors (more subtle and blended)
        for i in range(len(low_band)):
            x = i * bar_width
            
            # Calculate combined amplitude (use max of all bands)
            max_amp = max(low_band[i], mid_band[i], high_band[i])
            if max_amp == 0:
                continue
            
            bar_height = max_amp * (height / 2) * 0.9
            
            # Determine dominant frequency and blend colors
            # Normalize band values
            total = low_band[i] + mid_band[i] + high_band[i]
            if total == 0:
                continue
            
            low_ratio = low_band[i] / total
            mid_ratio = mid_band[i] / total
            high_ratio = high_band[i] / total
            
            # Blend colors based on frequency content
            # Blue (bass), Pink (mid), Red (high)
            r = int((low_ratio * 80 + mid_ratio * 255 + high_ratio * 255) * intensity)
            g = int((low_ratio * 120 + mid_ratio * 80 + high_ratio * 60) * intensity)
            b = int((low_ratio * 255 + mid_ratio * 180 + high_ratio * 100) * intensity)
            
            # Clamp values
            r = min(255, max(0, r))
            g = min(255, max(0, g))
            b = min(255, max(0, b))
            
            # Draw single bar with blended color
            painter.setBrush(QColor(r, g, b, 200))
            painter.setPen(Qt.NoPen)
            painter.drawRect(
                int(x),
                int(y_center - bar_height),
                max(1, int(bar_width)),
                int(bar_height * 2)
            )
    
    def _draw_simple_waveform(self, painter: QPainter, width: int, height: int):
        """Draw simple waveform with gradient (fallback)"""
        # Create gradient
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, self.gradient_start)
        gradient.setColorAt(0.5, self.gradient_mid)
        gradient.setColorAt(1, self.gradient_end)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        
        # Calculate bar width
        bar_width = max(1, width / len(self.waveform_data))
        
        # Normalize waveform
        max_amplitude = np.max(self.waveform_data) if np.max(self.waveform_data) > 0 else 1.0
        
        # Draw bars
        for i, amplitude in enumerate(self.waveform_data):
            x = i * bar_width
            normalized_amp = amplitude / max_amplitude
            bar_height = normalized_amp * (height / 2) * 0.9
            
            # Draw symmetric bar
            y_center = height / 2
            painter.drawRect(
                int(x),
                int(y_center - bar_height),
                max(1, int(bar_width)),
                int(bar_height * 2)
            )
    
    def _draw_beat_grid(self, painter: QPainter):
        """Draw beat grid overlay"""
        width = self.width()
        height = self.height()
        
        # Draw 8 vertical lines
        num_markers = 8
        painter.setPen(QPen(self.grid_color, 1))
        
        for i in range(num_markers + 1):
            x = (i / num_markers) * width
            painter.drawLine(int(x), 0, int(x), height)
    
    def _draw_overlays(self, painter: QPainter):
        """Draw key/BPM overlays"""
        from PySide6.QtGui import QFont
        
        # Draw key if enabled
        if self.preferences.get('show_key', True) and self.track_key:
            painter.setPen(QColor(255, 255, 255))
            font = QFont()
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(10, 30, self.track_key)
        
        # Draw BPM if enabled
        if self.preferences.get('show_bpm', True) and self.track_bpm:
            painter.setPen(QColor(255, 255, 255))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            bpm_text = f"{int(self.track_bpm)} BPM"
            
            # Draw aligned to right
            metrics = painter.fontMetrics()
            bpm_width = metrics.horizontalAdvance(bpm_text)
            painter.drawText(self.width() - bpm_width - 10, 25, bpm_text)
            
        # Draw Energy if available (custom addition) - DISABLED
        # if hasattr(self, 'track_energy') and self.track_energy:
            # ... code removed ...
            # pass

    
    def mousePressEvent(self, event):
        """Handle mouse click to seek"""
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            width = self.width()
            if width > 0:
                position = max(0.0, min(1.0, x / width))
                self.seek_requested.emit(position)
                # Optimistically update playhead
                self.set_playhead_position(position)

    def _draw_playhead(self, painter: QPainter):
        """Draw playhead line"""
        width = self.width()
        height = self.height()
        
        x = self.playhead_position * width
        
        painter.setPen(QPen(self.playhead_color, 2))
        painter.drawLine(int(x), 0, int(x), height)
    
    def mousePressEvent(self, event):
        """Handle mouse click to seek"""
        if event.button() == Qt.LeftButton:
            position = event.pos().x() / self.width()
            self.position_clicked.emit(position)
    
    def clear(self):
        """Clear waveform"""
        self.waveform_data = None
        self.playhead_position = 0.0
        self.track_key = None
        self.track_bpm = None
        self.update()

