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
        
        self.setAlternatingRowColors(True)
        
        # Connect signals
        self.doubleClicked.connect(self._on_double_click)
        
        self._drag_start_pos = None

    def setModel(self, model):
        """Override setModel to hide columns after model is set"""
        super().setModel(model)
        if model:
            # Hide ID and Path columns by default
            # Need to import model class here to avoid circular import or use constant values
            # ID is col 0, Path is col 9
            self.setColumnHidden(0, True)  # ID
            self.setColumnHidden(9, True)  # Path


    def mousePressEvent(self, event):
        """Record start position for drag"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Manually trigger drag to ensure it works"""
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
            
        if not self._drag_start_pos:
            return
            
        from PySide6.QtWidgets import QApplication
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        self.startDrag(Qt.CopyAction)
        
    def _on_header_menu(self, pos):
        header = self.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._on_header_menu)
        
        self._populate_playlist_menu = None # Callback
    
    def _on_header_menu(self, pos):
        """Show header context menu to toggle columns"""
        header = self.horizontalHeader()
        menu = QMenu(self)
        
        model = self.model()
        if not model:
            return
            
        # Add checkable actions for each column
        for i in range(model.columnCount()):
            col_name = model.headerData(i, Qt.Horizontal)
            action = menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not header.isSectionHidden(i))
            action.setData(i)
            action.triggered.connect(lambda checked, col=i: header.setSectionHidden(col, not checked))
            
        menu.exec_(header.mapToGlobal(pos))
    
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
        
        from PySide6.QtGui import QDrag, QPixmap, QPainter, QColor, QPen
        drag = QDrag(self)
        drag.setMimeData(mime)
        
        # Create a pixmap for visual feedback
        rect = self.visualRect(indexes[0])
        pixmap = QPixmap(rect.size())
        pixmap.fill(Qt.transparent)
        
        # Get track title for display
        track = model.get_track(indexes[0].row())
        track_title = track.title if track and track.title else "Unknown Track"
        
        # Truncate if too long
        if len(track_title) > 40:
            track_title = track_title[:37] + "..."
        
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        painter.fillRect(pixmap.rect(), QColor(60, 60, 60))
        painter.setPen(QPen(Qt.white))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, track_title)
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        # Execute drag
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting drag with tracks: {track_ids}")
        
        result = drag.exec_(Qt.CopyAction)
        logger.info(f"Drag finished with result: {result}")
