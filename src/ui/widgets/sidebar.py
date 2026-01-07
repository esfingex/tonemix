"""
Collapsible sidebar for navigation
"""
from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QWidget, QVBoxLayout,
                               QMenu, QInputDialog, QMessageBox, QStyle, QDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QImage
import logging
import psutil
from src.database.repository import PlaylistRepository, TrackRepository
from src.utils.security import validate_playlist_name
from src.ui.dialogs.playlist import DeletePlaylistDialog
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SidebarTree(QTreeWidget):
    """Custom TreeWidget to handle drag and drop"""
    tracks_dropped = Signal(int, list)  # playlist_id, track_ids

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
        track_data = event.mimeData().data(
            "application/x-tonemix-track-ids").data().decode()
        try:
            track_ids = json.loads(track_data)
            self.tracks_dropped.emit(playlist_id, track_ids)
            event.acceptProposedAction()
        except Exception:
            event.ignore()


class Sidebar(QWidget):
    """
    Collapsible sidebar for navigation
    """
    # Signals
    playlist_created = Signal(str)
    playlist_selected = Signal(int)    # id
    item_selected = Signal(str, object)  # type, item
    tracks_dropped = Signal(int, list)  # playlist_id, track_ids
    add_tracks_requested = Signal(int)  # playlist_id
    transcode_playlist_requested = Signal(int, str)  # playlist_id, format

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Navigation Tree
        self.tree = SidebarTree()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)  # Reduced for minimalist look
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

        # Connect expansion/collapse for icon updates - REMOVED for minimalist no-icon mode
        # self.tree.itemExpanded.connect(lambda i: self._update_icon_state(i, True))
        # self.tree.itemCollapsed.connect(lambda i: self._update_icon_state(i, False))

        layout.addWidget(self.tree)

        # Initialize items
        self._init_items()

        # Load devices
        self.refresh_devices()

    def _update_icon_state(self, item, expanded):
        """Update icon based on expansion state"""
        role = item.data(0, Qt.UserRole)
        style_id = None

        if role in ["root_library", "root_playlists"]:
            style_id = QStyle.SP_DirOpenIcon if expanded else QStyle.SP_DirIcon

        if style_id:
            item.setIcon(0, self._get_mono_icon(style_id))

    def _get_mono_icon(self, standard_id):
        """Get monochrome version of standard icon"""
        icon = self.style().standardIcon(standard_id)
        pixmap = icon.pixmap(20, 20)
        if pixmap.isNull():
            return icon

        # Convert to grayscale
        img = pixmap.toImage().convertToFormat(QImage.Format_Grayscale8)
        return QIcon(QPixmap.fromImage(img))

    def _init_items(self):
        """Initialize tree items"""
        # Minimalist Approach: No Icons, just clean text

        # Library Root
        self.library_root = QTreeWidgetItem(self.tree)
        self.library_root.setText(0, "LIBRARY")
        # self.library_root.setIcon(0, dir_icon) # Removed
        self.library_root.setExpanded(True)
        self.library_root.setData(0, Qt.UserRole, "root_library")
        # Make root items bold/distinct via font if possible, or just caps
        font = self.library_root.font(0)
        font.setBold(True)
        self.library_root.setFont(0, font)

        # All Tracks (always visible)
        self.all_tracks_item = QTreeWidgetItem(self.library_root)
        self.all_tracks_item.setText(0, "All Tracks")
        # self.all_tracks_item.setIcon(0, media_icon) # Removed
        self.all_tracks_item.setData(0, Qt.UserRole, "all_tracks")

        # Playlists Root
        self.playlists_root = QTreeWidgetItem(self.tree)
        self.playlists_root.setText(0, "PLAYLISTS")
        # self.playlists_root.setIcon(0, dir_icon) # Removed
        self.playlists_root.setExpanded(True)
        self.playlists_root.setData(0, Qt.UserRole, "root_playlists")
        self.playlists_root.setFont(0, font)

        # Devices Root
        self.devices_root = QTreeWidgetItem(self.tree)
        self.devices_root.setText(0, "DEVICES")
        # self.devices_root.setIcon(0, drive_icon) # Removed
        self.devices_root.setExpanded(True)
        self.devices_root.setData(0, Qt.UserRole, "root_devices")
        self.devices_root.setFont(0, font)

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
                is_media = ('/media/' in p.mountpoint or
                            '/run/media/' in p.mountpoint or
                            '/mnt/' in p.mountpoint)

                if is_media:
                    # Filter: Only show Rekordbox devices (must have PIONEER folder)
                    pioneer_path = Path(p.mountpoint) / "PIONEER"
                    if not pioneer_path.exists():
                        continue

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

                    # Scan for playlists on device
                    self._scan_device_playlists(item, p.mountpoint)

            self.devices_root.setExpanded(True)

        except Exception as e:
            logger.error(f"Error listing devices: {e}")

    def _scan_device_playlists(self, device_item: QTreeWidgetItem, mount_point: str):
        """Scan device for Rekordbox playlists (XML or PDB)"""
        try:
            mount_path = Path(mount_point)

            # 1. Try XML (Best compatibility if present)
            xml_loaded = False
            xml_candidates = [
                mount_path / "rekordbox.xml",
                mount_path / "PIONEER" / "rekordbox.xml",
                mount_path / "PIONEER" / "Rekordbox" / "rekordbox.xml"
            ]

            found_xml = None
            for xml in xml_candidates:
                if xml.exists():
                    found_xml = xml
                    break

            if found_xml:
                logger.info(f"Found XML on device: {found_xml}")
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(found_xml)
                    root = tree.getroot()

                    playlists_node = root.find('PLAYLISTS')
                    if playlists_node:
                        # Recursive function to add playlist nodes
                        def add_nodes(xml_node, parent_item):
                            for node in xml_node.findall('NODE'):
                                name = node.get('Name')
                                # 0=Folder, 1=Playlist
                                type_ = node.get('Type')

                                item = QTreeWidgetItem(parent_item)
                                item.setText(0, name)

                                if type_ == "0":  # Folder
                                    item.setIcon(
                                        0, self.style().standardIcon(QStyle.SP_DirIcon))
                                    add_nodes(node, item)
                                else:  # Playlist
                                    item.setIcon(0, self.style().standardIcon(
                                        QStyle.SP_FileIcon))
                                    # We can't easily play these yet without importing,
                                    # so maybe just show them for now?
                                    # Storing "xml_playlist" role to maybe handle click later
                                    item.setData(0, Qt.UserRole,
                                                 "device_playlist")
                                    # Store name or logic path
                                    item.setData(0, Qt.UserRole + 1, name)

                        root_node = playlists_node.find('NODE')
                        if root_node:
                            # Count total playlists for UI
                            try:
                                all_playlists = playlists_node.findall('.//NODE[@Type="1"]')
                                count = len(all_playlists)
                                current_text = device_item.text(0)
                                device_item.setText(0, f"{current_text} ({count})")
                            except:
                                pass # Ignore counting errors

                            add_nodes(root_node, device_item)
                            device_item.setExpanded(True)
                            xml_loaded = True
                except Exception as e:
                    logger.error(f"Error parsing device XML: {e}")

            # 2. Try PDB (Experimental) - Only if XML not used
            pdb_path = mount_path / "PIONEER" / "Rekordbox" / "export.pdb"
            if not xml_loaded and pdb_path.exists():
                logger.info(f"Found PDB on device: {pdb_path}")
                from src.importer.pdb_importer import DeviceSqlImporter
                importer = DeviceSqlImporter()
                if importer.open(str(pdb_path)):
                    playlists = importer.read_playlists()
                    if playlists:
                        # Update device header with count
                        current_text = device_item.text(0)
                        device_item.setText(0, f"{current_text} ({len(playlists)})")
                        
                        for pl in playlists:
                            pl_item = QTreeWidgetItem(device_item)
                            pl_item.setText(0, pl.get('name', 'Unknown'))
                            pl_item.setIcon(
                                0, self.style().standardIcon(QStyle.SP_FileIcon))
                            # Set Data for click handling
                            pl_item.setData(0, Qt.UserRole, "device_playlist_pdb")
                            pl_item.setData(0, Qt.UserRole + 1, pl.get('id'))
                            pl_item.setToolTip(0, "Imported from export.pdb (DeviceSQL)")
                    else:
                        # Show empty or "No Playlists / PDB Support Incomplete"
                        current_text = device_item.text(0)
                        device_item.setText(0, f"{current_text} (0)")
        except Exception as e:
            logger.error(f"Error scanning device playlists: {e}")

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
            rename_action.triggered.connect(
                lambda: self._rename_playlist(playlist_id, name))

            delete_action = menu.addAction("🗑️ Delete")
            delete_action.triggered.connect(
                lambda: self._delete_playlist(playlist_id, name))

            menu.addSeparator()

            add_tracks_action = menu.addAction("➕ Add Tracks from Files...")
            add_tracks_action.triggered.connect(
                lambda: self.add_tracks_requested.emit(playlist_id))

            # Transcode submenu
            transcode_menu = menu.addMenu("🎵 Transcode Playlist to...")
            transcode_aiff = transcode_menu.addAction("AIFF (24-bit)")
            transcode_aiff.triggered.connect(
                lambda: self.transcode_playlist_requested.emit(playlist_id, 'aiff'))
            transcode_wav = transcode_menu.addAction("WAV (24-bit)")
            transcode_wav.triggered.connect(
                lambda: self.transcode_playlist_requested.emit(playlist_id, 'wav'))
            transcode_mp3 = transcode_menu.addAction("MP3 (320kbps)")
            transcode_mp3.triggered.connect(
                lambda: self.transcode_playlist_requested.emit(playlist_id, 'mp3'))
            transcode_flac = transcode_menu.addAction("FLAC")
            transcode_flac.triggered.connect(
                lambda: self.transcode_playlist_requested.emit(playlist_id, 'flac'))

        if not menu.isEmpty():
            menu.exec_(self.tree.viewport().mapToGlobal(position))

    def _rename_playlist(self, playlist_id, current_name):
        new_name, ok = QInputDialog.getText(
            self, "Rename Playlist", "New Name:", text=current_name)
        if ok and new_name:
            if PlaylistRepository.update(playlist_id, {"name": new_name}):
                self.reload_playlists()

    def _delete_playlist(self, playlist_id, name):
        """Confirm and delete playlist"""
        dialog = DeletePlaylistDialog(name, self)
        if dialog.exec_() == QDialog.Accepted:

            # Check if we should delete files
            if dialog.should_delete_files():
                try:
                    # Get all tracks in playlist
                    tracks = PlaylistRepository.get_tracks(playlist_id)
                    deleted_files = 0

                    for track in tracks:
                        path = track.file_path
                        # Delete from DB (Track) - this should cascade to PlaylistTrack
                        # Note: If track is used in other playlists, it will be removed from them too
                        # because we are deleting the Asset.
                        if TrackRepository.delete(track.id):
                            # Delete from Disk
                            try:
                                if os.path.exists(path):
                                    os.remove(path)
                                    deleted_files += 1
                            except Exception as e:
                                logger.error(
                                    f"Error deleting file {path}: {e}")

                    # Finally delete playlist
                    PlaylistRepository.delete(playlist_id)
                    self.reload_playlists()

                    if deleted_files > 0:
                        QMessageBox.information(self, "Deleted",
                                                f"Deleted playlist '{name}' and {deleted_files} audio files from disk.")
                    else:
                        QMessageBox.warning(self, "Warning",
                                            f"Deleted playlist '{name}' but could not delete files (or none found).")

                except Exception as e:
                    logger.error(f"Delete error: {e}")
                    QMessageBox.critical(
                        self, "Error", f"Failed to delete: {e}")
            else:
                # Standard delete (Playlist only)
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
            QMessageBox.warning(
                self, "Error", f"Failed to reload playlists: {e}")

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
                    QMessageBox.critical(
                        self, "Error", "Failed to create playlist in database")
            except ValueError as e:
                QMessageBox.warning(self, "Invalid Name", str(e))

    def add_playlist(self, name: str, playlist_id: int = None):
        """Add playlist to tree"""
        item = QTreeWidgetItem(self.playlists_root)
        item.setText(0, name)
        item.setData(0, Qt.UserRole, "playlist")
        if playlist_id:
            item.setData(0, Qt.UserRole + 1, playlist_id)  # Store playlist ID
