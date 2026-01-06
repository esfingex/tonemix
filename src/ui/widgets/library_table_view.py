"""
Library table view with custom delegates
"""
from PySide6.QtWidgets import (QTableView, QStyledItemDelegate, QStyle, 
                                QStyleOptionViewItem, QMenu, QHeaderView)
from PySide6.QtCore import Qt, Signal, QModelIndex, QSize, QEvent, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QFont
import logging

from src.utils.camelot import get_key_color

logger = logging.getLogger(__name__)


class ArtworkDelegate(QStyledItemDelegate):
    """Custom delegate for rendering album artwork thumbnails"""
    
    def paint(self, painter, option, index):
        """Paint artwork"""
        artwork_data = index.data(Qt.UserRole + 2) # Artwork data role
        
        if artwork_data:
            pixmap = QPixmap()
            pixmap.loadFromData(artwork_data)
        else:
            # Placeholder or empty
            return
            
        # Draw image
        if not pixmap.isNull():
            # Center vertically
            size = min(option.rect.height() - 4, 90)
            x = option.rect.x() + 5
            y = option.rect.y() + (option.rect.height() - size) // 2
            
            target_rect = QRect(x, y, size, size)
            painter.drawPixmap(target_rect, pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def sizeHint(self, option, index):
        """Return size hint"""
        return QSize(100, 100)  # 90px image + padding


class KeyDelegate(QStyledItemDelegate):
    """Custom delegate for rendering Camelot keys with color"""
    
    def paint(self, painter, option, index):
        """Paint key with colored background"""
        key = index.data()
        
        if not key:
            return super().paint(painter, option, index)
        
        # Get color for key
        r, g, b = get_key_color(key)
        color = QColor(r, g, b)
        
        # Draw background
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        
        # Rounded rectangle
        rect = option.rect.adjusted(4, 4, -4, -4)
        painter.drawRoundedRect(rect, 4, 4)
        
        # Draw text
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        text_color = Qt.white if luminance < 128 else Qt.black
        painter.setPen(QPen(text_color))
        
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        
        painter.drawText(rect, Qt.AlignCenter, key)
    
    def sizeHint(self, option, index):
        """Return size hint"""
        return QSize(50, 30)


class RatingDelegate(QStyledItemDelegate):
    """Custom delegate for star ratings"""
    
    clicked = Signal(QModelIndex, int)  # index, new_rating
    
    def paint(self, painter, option, index):
        """Paint star rating"""
        rating = index.data() or 0
        
        # Draw background if selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        # Draw stars
        star_size = 16
        star_spacing = 2
        x_start = option.rect.x() + 5
        y = option.rect.y() + (option.rect.height() - star_size) // 2
        
        for i in range(5):
            x = x_start + (i * (star_size + star_spacing))
            
            if i < rating:
                # Filled star
                painter.setPen(QPen(QColor(255, 200, 0)))
                painter.setBrush(QBrush(QColor(255, 200, 0)))
            else:
                # Empty star
                painter.setPen(QPen(QColor(100, 100, 100)))
                painter.setBrush(Qt.NoBrush)
            
            # Draw star shape (simplified as circle for now)
            painter.drawEllipse(x, y, star_size, star_size)
    
    def editorEvent(self, event, model, option, index):
        """Handle click to change rating"""
        if event.type() == QEvent.MouseButtonRelease:
            x = event.pos().x() - option.rect.x() - 5
            star_size = 16
            star_spacing = 2
            
            # Calculate which star was clicked
            new_rating = min(5, max(0, int(x / (star_size + star_spacing)) + 1))
            
            # Emit signal
            self.clicked.emit(index, new_rating)
            return True
        
        return super().editorEvent(event, model, option, index)
    
    def sizeHint(self, option, index):
        """Return size hint"""
        return QSize(100, 30)


class LibraryTableView(QTableView):
    """Custom table view for music library"""
    
    # Signals
    track_double_clicked = Signal(int)  # track_id
    analyze_requested = Signal(list)  # list of track_ids
    load_to_deck_requested = Signal(int, str)  # track_id, deck_id
    transcode_requested = Signal(list, str)  # list of track_ids, format
    export_requested = Signal(list)  # list of track_ids
    transcode_requested = Signal(list)  # list of track_ids
    export_requested = Signal(list)  # list of track_ids
    delete_requested = Signal(list)  # list of track_ids
    files_dropped = Signal(list)  # list of file paths
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup table
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Enable drag
        # Enable drag and drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTableView.DragDrop)
        self.setDropIndicatorShown(True)
        
        # Setup headers
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._show_header_menu)
        self.verticalHeader().setVisible(False)
        
        # Connect signals
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.doubleClicked.connect(self._on_double_click)
        
        # Custom delegates
        self.artwork_delegate = ArtworkDelegate(self)
        self.key_delegate = KeyDelegate(self)
        self.rating_delegate = RatingDelegate(self)
        self.rating_delegate.clicked.connect(self._on_rating_clicked)
    
    def set_delegates(self, artwork_column: int, key_column: int, rating_column: int):
        """Set custom delegates for columns"""
        self.setItemDelegateForColumn(artwork_column, self.artwork_delegate)
        self.setItemDelegateForColumn(key_column, self.key_delegate)
        self.setItemDelegateForColumn(rating_column, self.rating_delegate)
        
        # Set fixed width for artwork column
        self.setColumnWidth(artwork_column, 100)
    
    def mousePressEvent(self, event):
        """Handle mouse press for drag init"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag start"""
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if not self._drag_start_pos:
            return
            
        from PySide6.QtWidgets import QApplication
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        self.startDrag(Qt.CopyAction)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Delete:
            selected_ids = self.get_selected_track_ids()
            if selected_ids:
                self.delete_requested.emit(selected_ids)
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        """Handle drag move"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            event.accept()
            files = []
            for url in event.mimeData().urls():
                files.append(url.toLocalFile())
            
            if files:
                self.files_dropped.emit(files)
        else:
            super().dropEvent(event)

    def _on_double_click(self, index: QModelIndex):
        """Handle double click"""
        if index.isValid():
            # Use robust method: get track from model
            track = self.model().get_track(index.row())
            if track and track.id:
                self.track_double_clicked.emit(track.id)

    def _show_header_menu(self, position):
        """Show context menu for header"""
        header = self.horizontalHeader()
        menu = QMenu(self)
        
        # Add actions to toggle columns
        model = self.model()
        if not model:
            return
            
        for col in range(model.columnCount()):
            # Get header name
            name = model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
            if not name:
                continue
                
            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(col))
            # Use default argument to capture column
            action.triggered.connect(lambda checked: self.setColumnHidden(col, not checked))
            
        menu.exec_(header.mapToGlobal(position))

    def setModel(self, model):
        """Override setModel to hide columns after model is set"""
        super().setModel(model)
        if model:
            # Hide ID and Path columns by default
            # ID is col 0, Path is col 9
            self.setColumnHidden(0, True)  # ID
            self.setColumnHidden(9, True)  # Path
    
    def _on_rating_clicked(self, index: QModelIndex, new_rating: int):
        """Handle rating change"""
        # Update model
        self.model().setData(index, new_rating, Qt.EditRole)
    
    def _show_context_menu(self, position: QPoint):
        """Show context menu"""
        menu = QMenu(self)
        
        # Get selected rows
        # Get selected rows
        selected_rows = self.selectionModel().selectedRows()
        
        # If no selection, select the row under context menu
        if not selected_rows:
            index = self.indexAt(position)
            if index.isValid():
                self.selectionModel().select(index, self.selectionModel().Select | self.selectionModel().Rows)
                selected_rows = self.selectionModel().selectedRows()
        
        if not selected_rows:
            logger.warning("Context menu: No rows selected")
            return
        
        # Get track IDs
        track_ids = self.get_selected_track_ids()
        
        if not track_ids:
            logger.warning("Context menu: No rows/tracks selected")
            return
            
        logger.info(f"Context menu for track IDs: {track_ids}")
        
        # Actions
        load_a = menu.addAction("🎵 Load to Deck A")
        load_a.triggered.connect(lambda: self.load_to_deck_requested.emit(track_ids[0], "A"))
        
        load_b = menu.addAction("🎵 Load to Deck B")
        load_b.triggered.connect(lambda: self.load_to_deck_requested.emit(track_ids[0], "B"))
        
        menu.addSeparator()
        
        analyze_action = menu.addAction("🔍 Analyze")
        reanalyze_action = menu.addAction("🔄 Re-analyze")
        menu.addSeparator()
        
        # Send to Playlist submenu
        playlist_menu = menu.addMenu("📋 Send to Playlist")
        # This will be populated by the main window
        self._populate_playlist_menu(playlist_menu, track_ids)
        menu.addSeparator()
        
        # Transcode submenu
        transcode_menu = menu.addMenu("🎵 Transcode to...")
        transcode_aiff = transcode_menu.addAction("AIFF (24-bit)")
        transcode_wav = transcode_menu.addAction("WAV (24-bit)")
        transcode_mp3 = transcode_menu.addAction("MP3 (320kbps)")
        transcode_flac = transcode_menu.addAction("FLAC")
        menu.addSeparator()
        
        export_action = menu.addAction("📤 Export to Rekordbox")
        menu.addSeparator()
        
        delete_action = QMenu.addAction(menu, "🗑️ Delete from Library")
        
        # Execute menu
        action = menu.exec_(self.viewport().mapToGlobal(position))
        
        # Handle actions
        if action == analyze_action or action == reanalyze_action:
            self.analyze_requested.emit(track_ids)
        elif action == transcode_aiff:
            self.transcode_requested.emit(track_ids, 'aiff')
        elif action == transcode_wav:
            self.transcode_requested.emit(track_ids, 'wav')
        elif action == transcode_mp3:
            self.transcode_requested.emit(track_ids, 'mp3')
        elif action == transcode_flac:
            self.transcode_requested.emit(track_ids, 'flac')
        elif action == export_action:
            self.export_requested.emit(track_ids)
        elif action == delete_action:
            self.delete_requested.emit(track_ids)
    
    def _populate_playlist_menu(self, menu, track_ids):
        """Populate playlist submenu - to be overridden or connected"""
        # This is a placeholder - the main window will set a proper handler
        menu.addAction("No playlists available")
    
    def _show_header_menu(self, position):
        """Show context menu for header columns"""
        header = self.horizontalHeader()
        menu = QMenu(self)
        
        model = self.model()
        if not model:
            return
            
        for col in range(model.columnCount()):
            # Skip ID column (always hidden or specifically handled)
            if col == 0:  # ID
                continue
                 
            action = menu.addAction(model.headerData(col, Qt.Horizontal))
            action.setCheckable(True)
            action.setChecked(not header.isSectionHidden(col))
            
            # Create a proper closure to toggle visibility
            def make_toggle(column, act):
                def toggle():
                    header.setSectionHidden(column, not act.isChecked())
                return toggle
            
            action.triggered.connect(make_toggle(col, action))
            
        menu.exec_(header.mapToGlobal(position))
    
    def startDrag(self, supportedActions):
        """Start drag operation with track IDs"""
        from PySide6.QtCore import QMimeData, QByteArray, QPoint
        from PySide6.QtGui import QDrag, QPixmap, QPainter, QColor
        import json
        
        track_ids = self.get_selected_track_ids()
        if not track_ids:
            return
        
        # Create mime data with track IDs
        mime_data = QMimeData()
        mime_data.setText(json.dumps(track_ids))
        mime_data.setData("application/x-tonemix-track-ids", QByteArray(json.dumps(track_ids).encode()))
        
        # Create drag
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # Visual feedback
        try:
            indexes = self.selectionModel().selectedRows()
            if indexes:
                logger.info("Creating drag visual feedback...")
                rect = self.visualRect(indexes[0])
                if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                    pixmap = QPixmap(rect.size())
                    pixmap.fill(Qt.transparent)
                    painter = QPainter(pixmap)
                    # Background
                    painter.fillRect(pixmap.rect(), QColor(64, 64, 64, 200)) # Semi-transparent dark
                    # Border
                    painter.setPen(QColor(0, 229, 255)) # Cyan
                    painter.drawRect(0, 0, pixmap.width()-1, pixmap.height()-1)
                    
                    # Draw Title
                    track = self.model().get_track(indexes[0].row())
                    if track and track.title:
                        painter.setPen(Qt.white)
                        font = painter.font()
                        font.setBold(True)
                        painter.setFont(font)
                        painter.drawText(pixmap.rect().adjusted(5, 0, -5, 0), Qt.AlignVCenter | Qt.AlignLeft, track.title)
                    
                    painter.end()
                    
                    drag.setPixmap(pixmap)
                    # HotSpot must be integer QPoint
                    drag.setHotSpot(QPoint(int(pixmap.width()/2), int(pixmap.height()/2)))
                    logger.info("Drag pixmap set successfully")
                else:
                    logger.warning(f"Invalid visual rect for drag: {rect}")
        except Exception as e:
            logger.error(f"Error creating drag pixmap: {e}")
        
        # Execute drag
        drag.exec_(Qt.CopyAction)
    
    def get_selected_track_ids(self) -> list:
        """Get list of selected track IDs"""
        track_ids = []
        selected_rows = self.selectionModel().selectedRows()
        
        if not selected_rows:
            return []
            
        for row in selected_rows:
            # Use robust method: get track object directly from model by row index
            # This works even if columns are hidden or moved
            track = self.model().get_track(row.row())
            if track and track.id:
                track_ids.append(track.id)
                
        return track_ids
