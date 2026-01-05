"""
Library table view with custom delegates
"""
from PySide6.QtWidgets import (QTableView, QStyledItemDelegate, QStyle, 
                                QStyleOptionViewItem, QMenu, QHeaderView)
from PySide6.QtCore import Qt, Signal, QModelIndex, QSize, QEvent, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QFont
import logging

from src.utils.camelot import get_key_color

logger = logging.getLogger(__name__)


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
    transcode_requested = Signal(list)  # list of track_ids
    export_requested = Signal(list)  # list of track_ids
    delete_requested = Signal(list)  # list of track_ids
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup table
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Setup headers
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.verticalHeader().setVisible(False)
        
        # Connect signals
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.doubleClicked.connect(self._on_double_click)
        
        # Custom delegates
        self.key_delegate = KeyDelegate(self)
        self.rating_delegate = RatingDelegate(self)
        self.rating_delegate.clicked.connect(self._on_rating_clicked)
    
    def set_delegates(self, key_column: int, rating_column: int):
        """Set custom delegates for columns"""
        self.setItemDelegateForColumn(key_column, self.key_delegate)
        self.setItemDelegateForColumn(rating_column, self.rating_delegate)
    
    def _on_double_click(self, index: QModelIndex):
        """Handle double click"""
        if index.isValid():
            # Get track ID from model (assuming it's in column 0)
            track_id = self.model().data(self.model().index(index.row(), 0))
            if track_id:
                self.track_double_clicked.emit(track_id)
    
    def _on_rating_clicked(self, index: QModelIndex, new_rating: int):
        """Handle rating change"""
        # Update model
        self.model().setData(index, new_rating, Qt.EditRole)
    
    def _show_context_menu(self, position: QPoint):
        """Show context menu"""
        menu = QMenu(self)
        
        # Get selected rows
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # Get track IDs
        track_ids = [self.model().data(self.model().index(row.row(), 0)) 
                     for row in selected_rows]
        
        # Actions
        analyze_action = menu.addAction("🔍 Analyze")
        reanalyze_action = menu.addAction("🔄 Re-analyze")
        menu.addSeparator()
        
        transcode_action = menu.addAction("🎵 Transcode to AIFF")
        menu.addSeparator()
        
        export_action = menu.addAction("📤 Export to Rekordbox")
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ Delete from Library")
        delete_action.setStyleSheet("color: #f44336;")
        
        # Execute menu
        action = menu.exec_(self.viewport().mapToGlobal(position))
        
        # Handle actions
        if action == analyze_action or action == reanalyze_action:
            self.analyze_requested.emit(track_ids)
        elif action == transcode_action:
            self.transcode_requested.emit(track_ids)
        elif action == export_action:
            self.export_requested.emit(track_ids)
        elif action == delete_action:
            self.delete_requested.emit(track_ids)
    
    def get_selected_track_ids(self) -> list:
        """Get list of selected track IDs"""
        selected_rows = self.selectionModel().selectedRows()
        return [self.model().data(self.model().index(row.row(), 0)) 
                for row in selected_rows]
