"""
Waveform preferences dialog
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                                QComboBox, QCheckBox, QSlider, QLabel, QPushButton)
from PySide6.QtCore import Qt, Signal
import logging

logger = logging.getLogger(__name__)


class WaveformPreferencesDialog(QDialog):
    """Dialog for waveform display preferences"""
    
    preferences_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Waveform Preferences")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Color scheme
        color_group = QGroupBox("Color Scheme")
        color_layout = QVBoxLayout(color_group)
        
        self.color_scheme = QComboBox()
        self.color_scheme.addItems([
            "Rekordbox (RGB Spectrum)",
            "RGB Spectrum",
            "Monochrome Blue",
            "Monochrome Green",
            "Monochrome Orange"
        ])
        color_layout.addWidget(QLabel("Waveform Colors:"))
        color_layout.addWidget(self.color_scheme)
        
        layout.addWidget(color_group)
        
        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        self.show_artwork = QCheckBox("Show Album Artwork")
        self.show_artwork.setChecked(True)
        display_layout.addWidget(self.show_artwork)
        
        self.show_key = QCheckBox("Show Key/Tonality")
        self.show_key.setChecked(True)
        display_layout.addWidget(self.show_key)
        
        self.show_bpm = QCheckBox("Show BPM")
        self.show_bpm.setChecked(True)
        display_layout.addWidget(self.show_bpm)
        
        self.show_beat_grid = QCheckBox("Show Beat Grid")
        self.show_beat_grid.setChecked(False)
        display_layout.addWidget(self.show_beat_grid)
        
        layout.addWidget(display_group)
        
        # Color intensity
        intensity_group = QGroupBox("Color Intensity")
        intensity_layout = QVBoxLayout(intensity_group)
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(50)
        self.intensity_slider.setMaximum(150)
        self.intensity_slider.setValue(100)
        self.intensity_slider.setTickPosition(QSlider.TicksBelow)
        self.intensity_slider.setTickInterval(25)
        
        self.intensity_label = QLabel("100%")
        self.intensity_slider.valueChanged.connect(
            lambda v: self.intensity_label.setText(f"{v}%")
        )
        
        intensity_layout.addWidget(QLabel("Intensity:"))
        intensity_layout.addWidget(self.intensity_slider)
        intensity_layout.addWidget(self.intensity_label)
        
        layout.addWidget(intensity_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self._ok)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(apply_button)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def _apply(self):
        """Apply preferences"""
        prefs = self.get_preferences()
        self.preferences_changed.emit(prefs)
    
    def _ok(self):
        """Apply and close"""
        self._apply()
        self.accept()
    
    def get_preferences(self):
        """Get current preferences"""
        return {
            'color_scheme': self.color_scheme.currentIndex(),
            'show_artwork': self.show_artwork.isChecked(),
            'show_key': self.show_key.isChecked(),
            'show_bpm': self.show_bpm.isChecked(),
            'show_beat_grid': self.show_beat_grid.isChecked(),
            'intensity': self.intensity_slider.value() / 100.0
        }
    
    def set_preferences(self, prefs):
        """Set preferences"""
        self.color_scheme.setCurrentIndex(prefs.get('color_scheme', 0))
        self.show_artwork.setChecked(prefs.get('show_artwork', True))
        self.show_key.setChecked(prefs.get('show_key', True))
        self.show_bpm.setChecked(prefs.get('show_bpm', True))
        self.show_beat_grid.setChecked(prefs.get('show_beat_grid', False))
        self.intensity_slider.setValue(int(prefs.get('intensity', 1.0) * 100))
