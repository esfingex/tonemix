"""
Waveform visualization widget
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPointF
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
        
        # Colors
        self.bg_color = QColor(42, 42, 42)
        self.grid_color = QColor(80, 80, 80)
        self.playhead_color = QColor(255, 200, 0)
        
        # Gradient colors (pink/purple)
        self.gradient_start = QColor(255, 100, 200, 180)
        self.gradient_mid = QColor(200, 100, 255, 200)
        self.gradient_end = QColor(255, 100, 200, 180)
        
        # Settings
        self.setMinimumHeight(120)
        self.setMouseTracking(True)
    
    def set_waveform(self, waveform_data: np.ndarray, duration: float = 0.0):
        """
        Set waveform data
        
        Args:
            waveform_data: Numpy array of waveform amplitudes
            duration: Duration in seconds
        """
        self.waveform_data = waveform_data
        self.duration = duration
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
            self._draw_beat_grid(painter)
        else:
            # Draw placeholder text
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No waveform loaded")
        
        # Draw playhead
        self._draw_playhead(painter)
    
    def _draw_waveform(self, painter: QPainter):
        """Draw the waveform with gradient"""
        width = self.width()
        height = self.height()
        
        if len(self.waveform_data) == 0:
            return
        
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
            bar_height = normalized_amp * (height / 2) * 0.9  # 90% of half height
            
            # Draw symmetric bar (top and bottom)
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
            
            # Draw marker number
            if i < num_markers:
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(int(x) + 5, 15, str(i + 1))
                painter.setPen(QPen(self.grid_color, 1))
    
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
        self.update()
