"""
Table model for track library
"""
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List
import logging

from src.database.models import Track

logger = logging.getLogger(__name__)


class TrackTableModel(QAbstractTableModel):
    """Table model for displaying tracks"""
    
    # Column indices
    COL_ARTWORK = 0  # New column
    COL_ID = 1
    COL_TITLE = 2
    COL_ARTIST = 3
    COL_ALBUM = 4
    COL_KEY = 5
    COL_BPM = 6
    COL_ENERGY = 7
    COL_DURATION = 8
    COL_RATING = 9
    COL_PATH = 10
    
    HEADERS = [
        "Art", "ID", "Title", "Artist", "Album", "Key", 
        "BPM", "Energy", "Duration", "Rating", "Path"
    ]
    
    def __init__(self, tracks: List[Track] = None, parent=None):
        super().__init__(parent)
        self._tracks = tracks or []
    
    def rowCount(self, parent=QModelIndex()):
        """Return number of rows"""
        return len(self._tracks)
    
    def columnCount(self, parent=QModelIndex()):
        """Return number of columns"""
        return len(self.HEADERS)

    def flags(self, index):
        """Return item flags - Critical for Drag & Drop"""
        if not index.isValid():
            return Qt.NoItemFlags
        
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEditable
    
    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Return data for index"""
        if not index.isValid() or not (0 <= index.row() < len(self._tracks)):
            return None
        
        track = self._tracks[index.row()]
        col = index.column()
        
        if role == Qt.ToolTipRole:
             if col in [self.COL_TITLE, self.COL_ARTIST, self.COL_ALBUM, self.COL_PATH]:
                 # Return specific text for primary columns
                 if col == self.COL_TITLE: return track.title
                 if col == self.COL_ARTIST: return track.artist
                 if col == self.COL_ALBUM: return track.album
                 if col == self.COL_PATH: return track.file_path
             return None # Fallback for others

        
        if role == Qt.UserRole + 2:  # Artwork Role
            if col == self.COL_ARTWORK:
                return track.artwork_thumbnail
        
        if role == Qt.DisplayRole:
            if col == self.COL_ARTWORK:
                return ""  # Drawn by delegate
            if col == self.COL_ID:
                return track.id
            elif col == self.COL_TITLE:
                return track.title or ""
            elif col == self.COL_ARTIST:
                return track.artist or ""
            elif col == self.COL_ALBUM:
                return track.album or ""
            elif col == self.COL_KEY:
                return track.key_camelot or ""
            elif col == self.COL_BPM:
                return f"{track.bpm:.1f}" if track.bpm else ""
            elif col == self.COL_ENERGY:
                return f"{track.energy_level:.1f}" if track.energy_level else ""
            elif col == self.COL_DURATION:
                if track.duration_seconds:
                    mins = int(track.duration_seconds // 60)
                    secs = int(track.duration_seconds % 60)
                    return f"{mins}:{secs:02d}"
                return ""
            elif col == self.COL_RATING:
                return track.rating or 0
            elif col == self.COL_PATH:
                return track.file_path or ""
        
        elif role == Qt.TextAlignmentRole:
            if col in [self.COL_BPM, self.COL_ENERGY, self.COL_DURATION, self.COL_RATING]:
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        return None
    
    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Set data for index"""
        if not index.isValid() or not (0 <= index.row() < len(self._tracks)):
            return False
        
        track = self._tracks[index.row()]
        col = index.column()
        
        if role == Qt.EditRole:
            if col == self.COL_RATING:
                track.rating = value
                self.dataChanged.emit(index, index)
                return True
        
        return False
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return header data"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None
    
    def flags(self, index: QModelIndex):
        """Return item flags"""
        if not index.isValid():
            return Qt.NoItemFlags
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        # Rating column is editable
        if index.column() == self.COL_RATING:
            flags |= Qt.ItemIsEditable
        
        return flags
    
    def set_tracks(self, tracks: List[Track]):
        """Update tracks data"""
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()
    
    def add_track(self, track: Track):
        """Add a track"""
        row = len(self._tracks)
        self.beginInsertRows(QModelIndex(), row, row)
        self._tracks.append(track)
        self.endInsertRows()
    
    def remove_track(self, row: int):
        """Remove a track"""
        if 0 <= row < len(self._tracks):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._tracks[row]
            self.endRemoveRows()
    
    def get_track(self, row: int) -> Track:
        """Get track at row"""
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def update_track(self, track: Track):
        """Update a track in the model"""
        for i, t in enumerate(self._tracks):
            if t.id == track.id:
                self._tracks[i] = track
                # Emit change for entire row
                self.dataChanged.emit(
                    self.index(i, 0),
                    self.index(i, self.columnCount() - 1)
                )
                break

    def sort(self, column: int, order):
        """Sort table by column"""
        self.layoutAboutToBeChanged.emit()
        
        reverse = (order == Qt.DescendingOrder)
        
        # Define sort key functions for each column
        if column == self.COL_ID:
            self._tracks.sort(key=lambda t: t.id or 0, reverse=reverse)
        elif column == self.COL_TITLE:
            self._tracks.sort(key=lambda t: (t.title or "").lower(), reverse=reverse)
        elif column == self.COL_ARTIST:
            self._tracks.sort(key=lambda t: (t.artist or "").lower(), reverse=reverse)
        elif column == self.COL_ALBUM:
            self._tracks.sort(key=lambda t: (t.album or "").lower(), reverse=reverse)
        elif column == self.COL_KEY:
            self._tracks.sort(key=lambda t: t.key_camelot or "", reverse=reverse)
        elif column == self.COL_BPM:
            self._tracks.sort(key=lambda t: t.bpm or 0, reverse=reverse)
        elif column == self.COL_ENERGY:
            self._tracks.sort(key=lambda t: t.energy_level or 0, reverse=reverse)
        elif column == self.COL_DURATION:
            self._tracks.sort(key=lambda t: t.duration_seconds or 0, reverse=reverse)
        elif column == self.COL_RATING:
            self._tracks.sort(key=lambda t: t.rating or 0, reverse=reverse)
        elif column == self.COL_PATH:
            self._tracks.sort(key=lambda t: (t.file_path or "").lower(), reverse=reverse)
        
        self.layoutChanged.emit()
