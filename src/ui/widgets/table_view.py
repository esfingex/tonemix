"""
Custom Table View for Library
"""
from PySide6.QtWidgets import QTableView, QMenu, QHeaderView, QStyledItemDelegate
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

class KeyDelegate(QStyledItemDelegate):
    """Delegate for coloring Camelot keys"""
    
    def paint(self, painter, option, index):
        """Paint key with color code"""
        key = index.data(Qt.DisplayRole)
        if not key:
            return
            
        painter.save()
        
        # Get color
        from src.utils.camelot import get_key_color
        r, g, b = get_key_color(str(key))
        color = QColor(r, g, b)
        
        # Draw background/badge
        rect = option.rect
        # Adjust rect for badge look
        badge_rect = QRect(rect.x() + 5, rect.y() + 2, rect.width() - 10, rect.height() - 4)
        
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(badge_rect, 4, 4)
        
        # Draw text
        # Check brightness for text color
        if (r * 0.299 + g * 0.587 + b * 0.114) > 160:
            text_color = QColor(0, 0, 0)
        else:
            text_color = QColor(255, 255, 255)
            
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignCenter, str(key))
        
        painter.restore()

class LibraryTableView(QTableView):
    """
    Custom QTableView with enhanced features
    """
    
    # Signals
    track_double_clicked = Signal(object) # track_id
    analyze_requested = Signal(list) # list of track_ids
    export_requested = Signal(list) # list of track_ids
    load_to_deck_requested = Signal(int, str) # track_id, deck_id ("A" or "B")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False) # Don't accept drops ON the table (reordering), only drag FROM it
        self.setDragEnabled(True)
        self.setDragDropMode(QTableView.DragOnly)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        
        # Connect signals
        self.doubleClicked.connect(self._on_double_click)
        
        self._populate_playlist_menu = None # Callback
    
    def set_delegates(self, key_column: int, rating_column: int):
        """Set custom item delegates"""
        self.key_column = key_column
        self.rating_column = rating_column
        
        # Set Key Delegate
        self.setItemDelegateForColumn(key_column, KeyDelegate(self))
        
    def _on_double_click(self, index):
        """Handle double click"""
        if not index.isValid():
            return
            
        # Emit signal to load track
        self.track_double_clicked.emit(index)
    
    def contextMenuEvent(self, event):
        """Handle context menu event"""
        menu = QMenu(self)
        
        # Add actions
        load_a = menu.addAction("Load to Deck A")
        load_a.triggered.connect(lambda: self._emit_load_to_deck("A"))
        
        load_b = menu.addAction("Load to Deck B")
        load_b.triggered.connect(lambda: self._emit_load_to_deck("B"))
        
        menu.addSeparator()
        
        analyze_action = menu.addAction("Analyze Selected Tracks")
        analyze_action.triggered.connect(self._emit_analyze)
        
        export_action = menu.addAction("Export to Rekordbox XML")
        export_action.triggered.connect(self._emit_export)
        
        menu.addSeparator()
        
        # Playlist submenu if callback is set
        if self._populate_playlist_menu:
            playlist_menu = menu.addMenu("Add to Playlist")
            indexes = self.selectionModel().selectedRows()
            track_ids = []
            # This is a bit hacky, normally model should give IDs
            # But we'll rely on MainWindow to handle the actual logic if we pass selection
            self._populate_playlist_menu(playlist_menu, track_ids)

        menu.exec_(event.globalPos())

    def _emit_load_to_deck(self, deck_id: str):
        """Emit load to deck signal for first selected track"""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return
            
        # Get first selected row's track ID
        # Accessing model directly
        model = self.model()
        index = indexes[0]
        track = model.get_track(index.row())
        
        if track:
            self.load_to_deck_requested.emit(track.id, deck_id)

    def _emit_analyze(self):
        """Emit analyze signal for selected tracks"""
        indexes = self.selectionModel().selectedRows()
        track_ids = [] # MainWindow logic will handle this better from selection
        self.analyze_requested.emit(track_ids) # Emit empty, MainWindow will check selection

    def _emit_export(self):
        """Emit export signal"""
        self.export_requested.emit([])
    
    def startDrag(self, actions):
        """Handle drag start"""
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return
            
        # Get track ID from model (assuming model has get_track)
        # We'll just drag the track ID as text/json
        import json
        from PySide6.QtCore import QMimeData
        
        # Get data from first selected row
        track_ids = []
        model = self.model()
        for index in indexes:
            # Assume model is TrackTableModel
            track = model.get_track(index.row())
            if track:
                track_ids.append(track.id)
        
        if not track_ids:
            return
            
        mime = QMimeData()
        mime.setData("application/x-tonemix-track-ids", json.dumps(track_ids).encode())
        
        from PySide6.QtGui import QDrag
        drag = QDrag(self)
        drag.setMimeData(mime)
        
        # Calculate pixmap for drag visual
        # drag.setPixmap(...) 
        
        drag.exec_(actions)
