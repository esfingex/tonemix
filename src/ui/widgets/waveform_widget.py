"""
Waveform visualization widget
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPointF, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QPixmap
import numpy as np
import logging

logger = logging.getLogger(__name__)


class WaveformWidget(QWidget):
    """Custom widget for waveform visualization"""
    
    # Signals
    seek_requested = Signal(float)  # Emits position (0.0 - 1.0)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.waveform_data = None
        self.playhead_position = 0.0  # 0.0 to 1.0
        self.duration = 0.0
        
        # Track metadata for overlays
        self.track_key = None
        self.track_bpm = None
        self.track_artwork = None
        
        # PHASE 2: QPixmap cache for 10-20x performance boost
        self._waveform_cache = None
        self._cache_zoom_level = None
        self._cache_position = None
        
        # Preferences
        self.preferences = {
            'color_scheme': 0,  # 0=Rekordbox, 1=RGB, 2=Mono Blue, etc.
            'show_artwork': True,
            'show_key': False,
            'show_bpm': False,
            'show_beat_grid': False,
            'intensity': 1.0
        }
        
        # Zoom/Scroll defaults
        self.visible_window = 10.0
        self.scrolling = True
        
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
        """
        self.waveform_data = waveform_data
        self.duration = duration
        self.track_key = key
        self.track_bpm = bpm
        self.track_energy = energy
        self.playhead_position = 0.0
        
        # Zoom settings
        self.visible_window = 10.0 # Show 10 seconds of audio when centered
        self.scrolling = True      # Enable scrolling mode by default per user request
        
        # Invalidate cache when new waveform loaded
        self._waveform_cache = None
        
        self.update()
    
    def set_playhead_position(self, position: float):
        """Set playhead position (0.0 to 1.0)"""
        self.playhead_position = max(0.0, min(1.0, position))
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse click to seek"""
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            width = self.width()
            if width <= 0:
                return

            if self.scrolling and self.duration > 0:
                # In scrolling mode, center is playhead.
                # Calculate time offset from center
                center_x = width / 2
                offset_x = x - center_x
                
                # Pixels per second
                pps = width / self.visible_window
                offset_seconds = offset_x / pps
                
                current_seconds = self.playhead_position * self.duration
                new_seconds = current_seconds + offset_seconds
                new_position = new_seconds / self.duration
                
                # Clamp
                new_position = max(0.0, min(1.0, new_position))
                self.seek_requested.emit(new_position)
                self.set_playhead_position(new_position)
            else:
                # Static mode (click to jump absolute)
                position = max(0.0, min(1.0, x / width))
                self.seek_requested.emit(position)
                self.set_playhead_position(position)

    def paintEvent(self, event):
        """Paint the waveform"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw background
            painter.fillRect(self.rect(), self.bg_color)
            
            # Draw waveform if data available
            if self.waveform_data is not None and len(self.waveform_data) > 0:
                if self.scrolling and self.duration > 0:
                    self._draw_scrolling_waveform(painter)
                else:
                    self._draw_waveform(painter)
                    
                if self.preferences.get('show_beat_grid', False):
                    self._draw_beat_grid(painter)
            else:
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(self.rect(), Qt.AlignCenter, "No waveform loaded")
            
            # Draw playhead
            self._draw_playhead(painter)
            
        except Exception as e:
            logger.error(f"Error in paintEvent: {e}")
        finally:
            if painter.isActive():
                painter.end()

    def wheelEvent(self, event):
        """Handle scroll wheel for zooming"""
        # Zoom factor
        factor = 1.1 if event.angleDelta().y() < 0 else 0.9
        
        # Update visible window (clamp between 1s and 60s)
        self.visible_window = max(1.0, min(60.0, self.visible_window * factor))
        
        # Invalidate cache on zoom change
        self._waveform_cache = None
        
        self.update()

    def _draw_scrolling_waveform(self, painter: QPainter):
        """Draw waveform with QPixmap caching for 10-20x performance"""
        width = self.width()
        height = self.height()
        
        if width <= 0 or height <= 0: return
        
        # Check if we can reuse cached pixmap
        current_time = self.playhead_position * self.duration
        needs_redraw = (
            self._waveform_cache is None or
            self._cache_zoom_level != self.visible_window or
            abs(self._cache_position - current_time) > (self.visible_window * 0.05)
        )
        
        if needs_redraw:
            # Render waveform to cache pixmap
            self._waveform_cache = QPixmap(width, height)
            self._waveform_cache.fill(self.bg_color)
            
            cache_painter = QPainter(self._waveform_cache)
            cache_painter.setRenderHint(QPainter.Antialiasing)
            
            # Render waveform to cache (rest of original logic)
            self._render_waveform_to_painter(cache_painter, width, height)
            
            cache_painter.end()
            
            # Update cache metadata
            self._cache_zoom_level = self.visible_window
            self._cache_position = current_time
        
        # Blit cached pixmap (super fast!)
        painter.drawPixmap(0, 0, self._waveform_cache)
    
    def _render_waveform_to_painter(self, painter: QPainter, width: int, height: int):
        """Render waveform to given painter (used for caching)"""
        
        # Calculate visible range
        current_time = self.playhead_position * self.duration
        start_time = current_time - (self.visible_window / 2)
        end_time = current_time + (self.visible_window / 2)
        
        # Get total samples
        if isinstance(self.waveform_data, dict):
            total_samples = len(self.waveform_data.get('low', []))
        else:
            total_samples = len(self.waveform_data)
        
        if total_samples == 0: return

        # Calculate indices
        sps = total_samples / self.duration
        start_idx = int(start_time * sps)
        end_idx = int(end_time * sps)
        
        # Handle out of bounds by padding or clamping? 
        # For speed, let's clamp and draw what we have
        safe_start = max(0, start_idx)
        safe_end = min(total_samples, end_idx)
        
        if safe_start >= safe_end: return

        # Extract visible chunk
        chunk_len = safe_end - safe_start
        
        # Calculate screen area for this chunk
        # Total visible time is visible_window
        # This chunk represents (chunk_len / sps) seconds
        # Fraction of screen = (chunk_len / sps) / visible_window
        
        chunk_screen_width = int(width * (chunk_len / (end_idx - start_idx)))
        if chunk_screen_width <= 0: return
        
        # Screen x offset
        px_offset = 0
        if start_idx < 0:
            px_offset = int(width * (abs(start_idx) / (end_idx - start_idx)))

        y_center = height / 2
        intensity = self.preferences.get('intensity', 1.0)
        
        # Vectorized Rendering
        if isinstance(self.waveform_data, dict):
            # Spectral - Get pointers
            low = self.waveform_data.get('low', [])
            mid = self.waveform_data.get('mid', [])
            high = self.waveform_data.get('high', [])
            
            # Slice once
            c_low = low[safe_start:safe_end]
            c_mid = mid[safe_start:safe_end]
            c_high = high[safe_start:safe_end]
            
            # Fast simple resampling:
            indices = np.linspace(0, chunk_len - 1, chunk_screen_width, dtype=int)
            
            # Efficient Max Pooling or Upscaling
            if chunk_len < chunk_screen_width:
                v_low = c_low[indices]
                v_mid = c_mid[indices]
                v_high = c_high[indices]
            else:
                bin_size = chunk_len // chunk_screen_width
                if bin_size < 1: bin_size = 1
                limit = bin_size * chunk_screen_width
                
                v_low = c_low[:limit].reshape(chunk_screen_width, bin_size).max(axis=1)
                v_mid = c_mid[:limit].reshape(chunk_screen_width, bin_size).max(axis=1)
                v_high = c_high[:limit].reshape(chunk_screen_width, bin_size).max(axis=1)
            
            # OPTIMIZATION: Vectorized color calculations with VIBRANT Rekordbox-style gradients
            max_amps = np.maximum(np.maximum(v_low, v_mid), v_high)
            totals = v_low + v_mid + v_high
            totals[totals == 0] = 1  # Avoid division by zero
            
            # MIXXX COLOR MAPPING (Correct):
            # Red = Bass (low frequencies)
            # Green = Mids (mid frequencies)
            # Blue = Highs (high frequencies)
            
            # Normalize each band to 0-1 range independently
            max_low = v_low.max() if v_low.max() > 0 else 1.0
            max_mid = v_mid.max() if v_mid.max() > 0 else 1.0
            max_high = v_high.max() if v_high.max() > 0 else 1.0
            
            norm_low = v_low / max_low
            norm_mid = v_mid / max_mid
            norm_high = v_high / max_high
            
            # Apply logarithmic scaling for better visual contrast
            # log(1 + x) compresses high values and expands low values
            norm_low = np.log1p(norm_low * 10) / np.log1p(10)
            norm_mid = np.log1p(norm_mid * 10) / np.log1p(10)
            norm_high = np.log1p(norm_high * 10) / np.log1p(10)
            
            # Scale to 0-255 with saturation boost (2.0x)
            saturation = 2.0
            low_contribution = (norm_low * 255 * intensity * saturation).astype(np.uint8)
            mid_contribution = (norm_mid * 255 * intensity * saturation).astype(np.uint8)
            high_contribution = (norm_high * 255 * intensity * saturation).astype(np.uint8)
            
            # MIXXX RGB MAPPING
            colors_r = np.clip(low_contribution, 0, 255).astype(np.uint8)   # Red = Bass
            colors_g = np.clip(mid_contribution, 0, 255).astype(np.uint8)   # Green = Mids
            colors_b = np.clip(high_contribution, 0, 255).astype(np.uint8)  # Blue = Highs
            
            # OPTIMIZATION: Disable antialiasing for bars (faster)
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setPen(Qt.NoPen)
            
            # OPTIMIZATION: Reuse QColor and QBrush objects
            color = QColor()
            brush = QBrush()
            
            for i in range(chunk_screen_width):
                if max_amps[i] <= 0.01: continue
                
                color.setRgb(int(colors_r[i]), int(colors_g[i]), int(colors_b[i]), 220)
                brush.setColor(color)
                painter.setBrush(brush)
                
                bar_h = max_amps[i] * (height/2) * 0.95
                x = px_offset + i
                painter.drawRect(x, int(y_center - bar_h), 1, int(bar_h * 2))
            
            painter.setRenderHint(QPainter.Antialiasing, True)
                
        else:
            # Simple Waveform
            chunk = self.waveform_data[safe_start:safe_end]
            
            if chunk_len < chunk_screen_width:
                # Upscale
                indices = np.linspace(0, chunk_len - 1, chunk_screen_width, dtype=int)
                vals = chunk[indices]
            else:
                # Downsample
                bin_size = chunk_len // chunk_screen_width
                if bin_size < 1: bin_size = 1
                limit = bin_size * chunk_screen_width
                vals = chunk[:limit].reshape(chunk_screen_width, bin_size).max(axis=1)
            
            painter.setPen(QColor(0, 229, 255, 230))
            for i in range(chunk_screen_width):
                val = vals[i]
                if val <= 0: continue
                bar_h = val * (height/2) * 0.95
                x = px_offset + i
                painter.drawLine(x, int(y_center - bar_h), x, int(y_center + bar_h))

    # Removed _draw_spectral_scrolling as it's merged above

    def _draw_playhead(self, painter: QPainter):
        """Draw playhead line"""
        width = self.width()
        height = self.height()
        
        if self.scrolling:
            x = width / 2
        else:
            x = self.playhead_position * width
        
        painter.setPen(QPen(self.playhead_color, 2))
        painter.drawLine(int(x), 0, int(x), height)

    def clear(self):
        """Clear waveform"""
        self.waveform_data = None
        self.playhead_position = 0.0
        self.track_key = None
        self.track_bpm = None
        self.update()

