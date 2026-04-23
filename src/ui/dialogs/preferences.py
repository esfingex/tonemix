"""
Preferences dialog with tabs
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                                QComboBox, QCheckBox, QSlider, QLabel, QPushButton,
                                QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
                                QHeaderView, QKeySequenceEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
import logging

from src.utils.config import config

logger = logging.getLogger(__name__)


class WaveformPreferencesWidget(QWidget):
    """Widget for waveform preferences"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
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
        self.show_key = QCheckBox("Show Key/Tonality")
        self.show_bpm = QCheckBox("Show BPM")
        self.show_beat_grid = QCheckBox("Show Beat Grid")
        
        display_layout.addWidget(self.show_artwork)
        display_layout.addWidget(self.show_key)
        display_layout.addWidget(self.show_bpm)
        display_layout.addWidget(self.show_beat_grid)
        layout.addWidget(display_group)
        
        # Color intensity
        intensity_group = QGroupBox("Color Intensity")
        intensity_layout = QVBoxLayout(intensity_group)
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(50, 150)
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
        
        layout.addStretch()

    def load_defaults(self, prefs):
        self.color_scheme.setCurrentIndex(prefs.get('color_scheme', 0))
        self.show_artwork.setChecked(prefs.get('show_artwork', True))
        self.show_key.setChecked(prefs.get('show_key', True))
        self.show_bpm.setChecked(prefs.get('show_bpm', True))
        self.show_beat_grid.setChecked(prefs.get('show_beat_grid', False))
        self.intensity_slider.setValue(int(prefs.get('intensity', 1.0) * 100))
        
    def get_preferences(self):
        return {
            'color_scheme': self.color_scheme.currentIndex(),
            'show_artwork': self.show_artwork.isChecked(),
            'show_key': self.show_key.isChecked(),
            'show_bpm': self.show_bpm.isChecked(),
            'show_beat_grid': self.show_beat_grid.isChecked(),
            'intensity': self.intensity_slider.value() / 100.0
        }


class ShortcutsWidget(QWidget):
    """Widget for keyboard shortcuts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.actions = {
            "play_deck_a": "Play/Pause Deck A",
            "play_deck_b": "Play/Pause Deck B",
            "cue_deck_a": "Cue Deck A",
            "cue_deck_b": "Cue Deck B",
            "load_deck_a": "Load to Deck A",
            "load_deck_b": "Load to Deck B",
            "delete_from_playlist": "Delete from Playlist/Library",
            "analyze_selected": "Analyze Selected",
            "transcode_selected": "Transcode Selected",
            "select_all": "Select All Tracks"
        }
        self.default_keys = {
            "play_deck_a": "Space",
            "play_deck_b": "Ctrl+Space",
            "cue_deck_a": "C",
            "cue_deck_b": "Ctrl+C",
            "load_deck_a": "Ctrl+1",
            "load_deck_b": "Ctrl+2",
            "delete_from_playlist": "Delete",
            "analyze_selected": "Ctrl+Shift+A",
            "transcode_selected": "Ctrl+T",
            "select_all": "Ctrl+A"
        }
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        # Make items editable by double clicking (handled by cellDoubleClicked)
        self.table.cellDoubleClicked.connect(self._edit_shortcut)
        
        layout.addWidget(self.table)
        
        help_label = QLabel("Double-click a shortcut to edit. Pres 'Esc' to clear.")
        help_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(help_label)
        
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        layout.addWidget(reset_btn)

    def load_shortcuts(self, shortcuts_config):
        self.table.setRowCount(0)
        
        # Merge defaults with config
        self.current_shortcuts = self.default_keys.copy()
        if shortcuts_config:
            self.current_shortcuts.update(shortcuts_config)
            
        for action_id, name in self.actions.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Action Name
            item_name = QTableWidgetItem(name)
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item_name.setData(Qt.UserRole, action_id)
            self.table.setItem(row, 0, item_name)
            
            # Shortcut
            key = self.current_shortcuts.get(action_id, "")
            item_key = QTableWidgetItem(key)
            item_key.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable) 
            # We don't use ItemIsEditable because we want to popup a recorder
            self.table.setItem(row, 1, item_key)
            
    def _edit_shortcut(self, row, col):
        if col != 1:
            return
            
        action_item = self.table.item(row, 0)
        key_item = self.table.item(row, 1)
        action_id = action_item.data(Qt.UserRole)
        
        # Show KeySequenceEdit dialog? Or inline?
        # Inline is tricky with QKeySequenceEdit inside table.
        # Let's use a small dialog.
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set Shortcut for {action_item.text()}")
        layout = QVBoxLayout(dialog)
        
        editor = QKeySequenceEdit(QKeySequence(key_item.text()))
        layout.addWidget(QLabel("Press key sequence:"))
        layout.addWidget(editor)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(editor.clear)
        btns.addWidget(ok_btn)
        btns.addWidget(clear_btn)
        layout.addLayout(btns)
        
        if dialog.exec_():
            new_seq = editor.keySequence().toString()
            key_item.setText(new_seq)
            self.current_shortcuts[action_id] = new_seq

    def _reset_defaults(self):
        self.load_shortcuts(self.default_keys)

    def get_shortcuts(self):
        return self.current_shortcuts


class PreferencesDialog(QDialog):
    """Main preferences dialog"""
    
    preferences_changed = Signal(dict)
    shortcuts_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tabs
        self.waveform_tab = WaveformPreferencesWidget()
        self.tabs.addTab(self.waveform_tab, "Waveform")
        
        self.shortcuts_tab = ShortcutsWidget()
        self.tabs.addTab(self.shortcuts_tab, "Shortcuts")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._ok)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Load Config
        self._load_config()
        
    def _load_config(self):
        # Waveform
        # We need to get current prefs from MainWindow or pass them in?
        # Ideally read from config.yaml if stored there, but waveform prefs 
        # seem to be transient in MainWindow or passed by signal?
        # MainWindow passes them. So we should have a `set_preferences` method.
        # But shortcuts are global.
        self.shortcuts_tab.load_shortcuts(config.shortcuts)
        
    def set_waveform_preferences(self, prefs):
        """Called by MainWindow to set initial state"""
        self.waveform_tab.load_defaults(prefs)
        
    def _ok(self):
        # Save Shortcuts
        shortcuts = self.shortcuts_tab.get_shortcuts()
        config.set('shortcuts', shortcuts)
        config.save()
        self.shortcuts_changed.emit(shortcuts)
        
        # Emit Waveform Prefs
        wf_prefs = self.waveform_tab.get_preferences()
        self.preferences_changed.emit(wf_prefs)
        
        self.accept()
