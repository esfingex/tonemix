"""
Collapsible sidebar for navigation
"""
from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout,
                                QMenu, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, Signal
import logging
import psutil
from src.ui.utils.icons import get_icon
from src.database.repository import PlaylistRepository
from src.utils.security import validate_playlist_name

logger = logging.getLogger(__name__)


class SidebarTree(QTreeWidget):
    """Custom TreeWidget to handle drag and drop"""
    tracks_dropped = Signal(int, list) # playlist_id, track_ids
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DropOnly)
    
    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasFormat("application/x-tonemix-track-ids"):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        """Handle drag move"""
        if event.mimeData().hasFormat("application/x-tonemix-track-ids"):
            # Check if hovering over a playlist item
            item = self.itemAt(event.pos())
            if item and item.data(0, Qt.UserRole) == "playlist":
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Handle drop"""
        import json
        
        if not event.mimeData().hasFormat("application/x-tonemix-track-ids"):
            event.ignore()
            return
        
        # Get dropped item
        item = self.itemAt(event.pos())
        if not item or item.data(0, Qt.UserRole) != "playlist":
            event.ignore()
            return
        
        # Get playlist ID
        playlist_id = item.data(0, Qt.UserRole + 1)
        if not playlist_id:
            event.ignore()
            return
        
        # Get track IDs from mime data
        track_data = event.mimeData().data("application/x-tonemix-track-ids").data().decode()
        try:
            track_ids = json.loads(track_data)
            self.tracks_dropped.emit(playlist_id, track_ids)
            event.acceptProposedAction()
        except:
            event.ignore()


class Sidebar(QWidget):
    """
    Collapsible sidebar for navigation
    """
    # Signals
    playlist_created = Signal(str)
    playlist_selected = Signal(int)    # id
    item_selected = Signal(str, object) # type, item
    tracks_dropped = Signal(int, list) # playlist_id, track_ids
    add_tracks_requested = Signal(int) # playlist_id
    transcode_playlist_requested = Signal(int, str) # playlist_id, format
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Navigation Tree
        self.tree = SidebarTree()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setUniformRowHeights(True)
        
        # Forward drop signal
        self.tree.tracks_dropped.connect(self.tracks_dropped.emit)
        
        # Connect signals
        self.tree.itemClicked.connect(self._on_item_clicked)
        # self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        
        # Connect signals
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.tree)
        
        # Initialize items
        self._init_items()
        
        # Load devices
        self.refresh_devices()
        
    def _init_items(self):
        """Initialize tree items"""
        # Library Root
        self.library_root = QTreeWidgetItem(self.tree)
        self.library_root.setText(0, "Library")
        self.library_root.setExpanded(True)
        self.library_root.setData(0, Qt.UserRole, "root_library")
        
        # All Tracks (always visible)
        self.all_tracks_item = QTreeWidgetItem(self.library_root)
        self.all_tracks_item.setText(0, "📚 All Tracks")
        self.all_tracks_item.setData(0, Qt.UserRole, "all_tracks")
        
        # Playlists Root
        self.playlists_root = QTreeWidgetItem(self.tree)
        self.playlists_root.setText(0, "Playlists")
        self.playlists_root.setExpanded(True)
        self.playlists_root.setData(0, Qt.UserRole, "root_playlists")
        
        # Devices Root
        self.devices_root = QTreeWidgetItem(self.tree)
        self.devices_root.setText(0, "Devices")
        self.devices_root.setExpanded(True)
        self.devices_root.setData(0, Qt.UserRole, "root_devices")
    
    def refresh_devices(self):
        """Scan and list mounted devices"""
        # Clear existing devices
        self.devices_root.takeChildren()
        
        try:
            partitions = psutil.disk_partitions()
            for p in partitions:
                # Filter useful partitions
                if 'loop' in p.device or not p.mountpoint:
                    continue
                
                # Check for removable drives or secondary mounts
                # On Linux, usually in /media or /run/media
                if '/media/' in p.mountpoint or '/run/media/' in p.mountpoint or '/mnt/' in p.mountpoint:
                    item = QTreeWidgetItem(self.devices_root)
                    
                    # Name: Use label if available (os.path.basename) or mountpoint
                    import os
                    name = os.path.basename(p.mountpoint)
                    if not name:
                        name = p.mountpoint
                    
                    item.setText(0, f"{name}")
                    item.setData(0, Qt.UserRole, "device")
                    item.setData(0, Qt.UserRole + 1, p.mountpoint)
                    item.setToolTip(0, f"{p.device} ({p.fstype})")
            
            self.devices_root.setExpanded(True)
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
        
    def _on_item_clicked(self, item, column):
        """Handle item click"""
        item_type = item.data(0, Qt.UserRole)
        self.item_selected.emit(item_type, item)
        
    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.tree.itemAt(position)
        if not item:
            return
            
        item_type = item.data(0, Qt.UserRole)
        menu = QMenu()
        
        if item_type == "root_playlists":
            action = menu.addAction("Create Playlist")
            action.triggered.connect(self._create_playlist_dialog)
            
        elif item_type == "root_devices":
            action = menu.addAction("Scan Devices")
            action.triggered.connect(self.refresh_devices)
            
        elif item_type == "playlist":
            playlist_id = item.data(0, Qt.UserRole + 1)
            name = item.text(0)
            
            rename_action = menu.addAction("✏️ Rename")
            rename_action.triggered.connect(lambda: self._rename_playlist(playlist_id, name))
            
            delete_action = menu.addAction("🗑️ Delete")
            delete_action.triggered.connect(lambda: self._delete_playlist(playlist_id, name))
            
            menu.addSeparator()
            
            add_tracks_action = menu.addAction("➕ Add Tracks from Files...")
            add_tracks_action.triggered.connect(lambda: self.add_tracks_requested.emit(playlist_id))
            
            # Transcode submenu
            transcode_menu = menu.addMenu("🎵 Transcode Playlist to...")
            transcode_aiff = transcode_menu.addAction("AIFF (24-bit)")
            transcode_aiff.triggered.connect(lambda: self.transcode_playlist_requested.emit(playlist_id, 'aiff'))
            transcode_wav = transcode_menu.addAction("WAV (24-bit)")
            transcode_wav.triggered.connect(lambda: self.transcode_playlist_requested.emit(playlist_id, 'wav'))
            transcode_mp3 = transcode_menu.addAction("MP3 (320kbps)")
            transcode_mp3.triggered.connect(lambda: self.transcode_playlist_requested.emit(playlist_id, 'mp3'))
            transcode_flac = transcode_menu.addAction("FLAC")
            transcode_flac.triggered.connect(lambda: self.transcode_playlist_requested.emit(playlist_id, 'flac'))
            
        if not menu.isEmpty():
            menu.exec_(self.tree.viewport().mapToGlobal(position))
            
    def _rename_playlist(self, playlist_id, current_name):
        new_name, ok = QInputDialog.getText(self, "Rename Playlist", "New Name:", text=current_name)
        if ok and new_name:
            if PlaylistRepository.update(playlist_id, {"name": new_name}):
                self.reload_playlists()

    def _delete_playlist(self, playlist_id, name):
        reply = QMessageBox.question(self, "Delete Playlist", 
                                   f"Are you sure you want to delete playlist '{name}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if PlaylistRepository.delete(playlist_id):
                self.reload_playlists()

    def reload_playlists(self):
        """Reload all playlists from database"""
        try:
            playlists = PlaylistRepository.get_all()
            if playlists is None:
                logger.error("Failed to fetch playlists (returned None)")
                return
                
            # Only clear if we successfully fetched
            self.playlists_root.takeChildren()
            
            for p in playlists:
                self.add_playlist(p.name, p.id)
                
            logger.info(f"Reloaded {len(playlists)} playlists")
        except Exception as e:
            logger.error(f"Error reloading playlists: {e}")
            # Don't clear children on error to preserve state if possible?
            # Or show error in UI?
            QMessageBox.warning(self, "Error", f"Failed to reload playlists: {e}")
            
    def _create_playlist_dialog(self):
        """Show create playlist dialog"""
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist Name:")
        if ok and name:
            try:
                # Validate name
                validate_playlist_name(name)
                
                # Create in DB
                from src.database.repository import PlaylistRepository
                p = PlaylistRepository.create(name)
                if p:
                    self.add_playlist(p.name, p.id)
                    self.playlist_created.emit(p.name)
                else:
                    QMessageBox.critical(self, "Error", "Failed to create playlist in database")
            except ValueError as e:
                QMessageBox.warning(self, "Invalid Name", str(e))
            
    def add_playlist(self, name: str, playlist_id: int = None):
        """Add playlist to tree"""
        item = QTreeWidgetItem(self.playlists_root)
        item.setText(0, name)
        item.setData(0, Qt.UserRole, "playlist")
        if playlist_id:
            item.setData(0, Qt.UserRole + 1, playlist_id)  # Store playlist ID

