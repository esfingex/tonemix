"""
Main application window
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QStatusBar, QProgressBar, QLabel,
                               QPushButton, QMessageBox, QFileDialog, QMenu,
                               QTableView, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
from pathlib import Path
import logging

from src.ui.widgets.waveform_widget import WaveformWidget
from src.ui.widgets.library_table_view import LibraryTableView
from src.ui.widgets.sidebar import Sidebar
from src.importer.rekordbox_importer import RekordboxImporter
from src.ui.widgets.audio_player import AudioPlayer
# from src.ui.widgets.drop_zone import DropZone
from src.ui.models import TrackTableModel, Track
from src.database.repository import TrackRepository, PlaylistRepository
from src.core.analyzer import AudioAnalyzer
from src.core.audio_processor import AudioProcessor
from src.core.transcoder import AudioTranscoder
from src.core.transcoder import AudioTranscoder
from src.export.rekordbox_exporter import RekordboxExporter
from src.ui.dialogs.preferences import PreferencesDialog
from src.ui.styles import get_main_stylesheet
from src.utils.config import config
from src.utils.security import validate_audio_file
from PySide6.QtGui import QKeySequence, QShortcut

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Worker thread for audio analysis (Multiprocessing)"""

    progress = Signal(int, int)  # current, total
    track_analyzed = Signal(str, object)  # file_path, TrackAnalysis
    finished = Signal()
    error = Signal(str)

    def __init__(self, file_paths: list):
        super().__init__()
        self.file_paths = file_paths
        # We don't instantiate AudioAnalyzer here anymore for the worker pool
        # It's instantiated per-process in run_single_analysis

    def run(self):
        """Run analysis in parallel"""
        from concurrent.futures import ProcessPoolExecutor
        import os
        from src.core.analyzer import run_single_analysis

        try:
            total = len(self.file_paths)
            # Leave one core free for UI
            max_workers = max(1, os.cpu_count() - 1)

            logger.info(
                f"Starting parallel analysis with {max_workers} workers")

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Map file paths to futures
                file_map = {executor.submit(
                    run_single_analysis, fp): fp for fp in self.file_paths}

                completed = 0
                from concurrent.futures import as_completed

                for future in as_completed(file_map):
                    file_path = file_map[future]
                    try:
                        result = future.result()
                        if result:
                            self.track_analyzed.emit(file_path, result)

                        completed += 1
                        self.progress.emit(completed, total)

                    except Exception as e:
                        logger.error(f"Error analyzing {file_path}: {e}")
                        self.error.emit(
                            f"Error analyzing {Path(file_path).name}: {str(e)}")

            self.finished.emit()

        except Exception as e:
            logger.error(f"Analysis worker error: {e}")
            self.error.emit(str(e))


class TranscodeWorker(QThread):
    """Worker thread for transcoding"""

    progress = Signal(int, int)  # current, total
    file_transcoded = Signal(int, str)  # original_track_id, new_file_path
    # finished = Signal()  # REMOVED: Use QThread.finished
    error = Signal(str)

    def __init__(self, track_files: dict, output_dir: str, target_format: str = 'aiff'):
        """
        Args:
            track_files: Dict {track_id: input_path}
            output_dir: Destination directory
            target_format: Output format (aiff, mp3, wav, flac)
        """
        super().__init__()
        self.track_files = track_files
        self.output_dir = output_dir
        self.target_format = target_format
        self.transcoder = AudioTranscoder()
        self._is_running = True
        self.timeout_seconds = 300  # 5 minutes max per file

    def run(self):
        """Run transcoding"""
        total = len(self.track_files)
        current = 0

        for track_id, input_path in self.track_files.items():
            if not self._is_running:
                break

            try:
                # Transcode logic
                # Determine output filename
                input_file = Path(input_path)
                output_path = str(Path(self.output_dir) /
                                  f"{input_file.stem}.{self.target_format}")

                result = self.transcoder.transcode_file(
                    input_path, output_path, self.target_format)

                if result:
                    self.file_transcoded.emit(track_id, result)
                else:
                    self.error.emit(f"Failed to transcode {input_file.name}")

                current += 1
                self.progress.emit(current, total)

            except Exception as e:
                logger.error(f"Transcode error for {input_path}: {e}")
                self.error.emit(
                    f"Error transcoding {Path(input_path).name}: {e}")

        # self.finished.emit() # REMOVED: QThread emits finished automatically

    def stop(self):
        self._is_running = False


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ToneMix Pro - Professional Music Analysis")
        self.setGeometry(100, 100, 1280, 720)

        # Components
        self.audio_processor = AudioProcessor()
        self.repository = TrackRepository()
        self.exporter = RekordboxExporter()

        # Shortcuts
        self._shortcuts = []
        self._setup_shortcuts()

        # Analysis worker
        self.analysis_worker = None

        # State
        self._current_playlist_id = None
        self._current_device_path = None
        self._is_loading_device = False

        # Setup UI
        self._create_menu_bar()
        self._create_toolbar()
        self._create_ui()
        self._create_status_bar()

        # Apply Styles
        self.setStyleSheet(get_main_stylesheet())

        # Load tracks
        self._load_tracks()

        # Load playlists
        self._load_playlists()

        # Select "All Tracks" by default
        if hasattr(self.sidebar, 'all_tracks_item'):
            self.sidebar.tree.setCurrentItem(self.sidebar.all_tracks_item)
            self._on_sidebar_item_selected(
                "all_tracks", self.sidebar.all_tracks_item)

        # Restore settings
        self._restore_settings()

        logger.info("Main window initialized")

    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        import_action = QAction("&Import Files...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._import_files)
        file_menu.addAction(import_action)

        import_folder_action = QAction("Import &Folder...", self)
        import_folder_action.setShortcut("Ctrl+Shift+I")
        import_folder_action.triggered.connect(self._import_folder)
        file_menu.addAction(import_folder_action)

        import_rekordbox_action = QAction(
            "Import from &Rekordbox XML...", self)
        import_rekordbox_action.triggered.connect(self._import_from_rekordbox)
        file_menu.addAction(import_rekordbox_action)

        file_menu.addSeparator()

        export_action = QAction("&Export to Rekordbox...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_to_rekordbox)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        refresh_action = QAction("&Refresh Library", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._load_tracks)
        view_menu.addAction(refresh_action)

        view_menu.addSeparator()

        settings_action = QAction("&Preferences...", self)
        settings_action.triggered.connect(self._show_preferences)
        view_menu.addAction(settings_action)

        # Create menu
        menu = QMenu(self)

        # Deck actions
        load_a_action = QAction("Load to Deck A", self)
        load_a_action.triggered.connect(self._load_to_deck_a)
        menu.addAction(load_a_action)

        load_b_action = QAction("Load to Deck B", self)
        load_b_action.triggered.connect(self._load_to_deck_b)
        menu.addAction(load_b_action)

        menu.addSeparator()

        analyze_action = QAction("Analyze Track(s)", self)
        analyze_action.triggered.connect(self._analyze_selected_tracks)
        menu.addAction(analyze_action)

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)

        # Toggle sidebar action
        self.toggle_sidebar_action = QAction("☰", self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        toolbar.addAction(self.toggle_sidebar_action)

    def _toggle_sidebar(self, checked):
        """Toggle sidebar visibility"""
        if checked:
            self.main_splitter.setSizes([200, 800])  # Restore
        else:
            self.main_splitter.setSizes([0, 1000])  # Collapse

    def _create_ui(self):
        """Create main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout (Vertical): Decks on top, Library on bottom
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Decks Area ---
        decks_container = QWidget()
        decks_layout = QHBoxLayout(decks_container)
        decks_layout.setContentsMargins(5, 5, 5, 5)
        decks_layout.setSpacing(10)

        # Deck A
        # Deck A
        from src.ui.widgets.deck import DeckWidget
        self.deck_a = DeckWidget("A")
        self.deck_a.track_dropped.connect(
            lambda t_id: self._load_track(t_id, "A"))
        decks_layout.addWidget(self.deck_a)

        # Deck B
        self.deck_b = DeckWidget("B")
        self.deck_b.track_dropped.connect(
            lambda t_id: self._load_track(t_id, "B"))
        decks_layout.addWidget(self.deck_b)

        main_layout.addWidget(decks_container, 1)  # Stretch factor 1

        # --- Library Area (Splitter) ---
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Sidebar (Left)
        self.sidebar = Sidebar()
        # Connect sidebar signals
        self.sidebar.playlist_selected.connect(self._on_sidebar_item_selected)
        self.sidebar.item_selected.connect(self._on_sidebar_item_selected)
        self.sidebar.playlist_created.connect(self._on_playlist_created)
        self.sidebar.add_tracks_requested.connect(
            self._add_tracks_to_playlist_dialog)
        self.sidebar.transcode_playlist_requested.connect(
            self._on_transcode_playlist_requested)
        self.sidebar.tracks_dropped.connect(self._add_tracks_to_playlist)
        self.main_splitter.addWidget(self.sidebar)

        # Track Table (Right)
        self.table_view = LibraryTableView()
        self.table_view.load_to_deck_requested.connect(self._load_track)
        # Connect drag & drop signal
        self.table_view.files_dropped.connect(self._import_dropped_files)
        self.table_model = TrackTableModel()
        self.table_view.setModel(self.table_model)

        # Set custom delegates
        self.table_view.set_delegates(
            artwork_column=TrackTableModel.COL_ARTWORK,
            key_column=TrackTableModel.COL_KEY,
            rating_column=TrackTableModel.COL_RATING
        )

        # Hide internal columns (ID and Path)
        self.table_view.setColumnHidden(TrackTableModel.COL_ID, True)
        self.table_view.setColumnHidden(TrackTableModel.COL_PATH, True)

        # Connect signals
        self.table_view.track_double_clicked.connect(
            self._on_table_double_clicked)
        self.table_view.analyze_requested.connect(self._on_analyze_requested)
        self.table_view.transcode_requested.connect(
            self._on_transcode_requested)  # New connection
        self.table_view.export_requested.connect(self._on_export_requested)
        self.table_view.delete_requested.connect(self._on_delete_requested)
        self.table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Override playlist menu population
        self.table_view._populate_playlist_menu = self._populate_playlist_menu

        self.main_splitter.addWidget(self.table_view)

        # Set splitter sizes
        self.main_splitter.setSizes([200, 800])
        self.main_splitter.setStretchFactor(1, 1)

        # Add splitter to main layout
        # Stretch factor 3 (larger than decks)
        main_layout.addWidget(self.main_splitter, 3)

    def _on_sidebar_item_selected(self, item_type, item):
        """Handle sidebar navigation"""
        if item_type == "playlist":
            # Load playlist tracks
            playlist_id = item.data(0, Qt.UserRole + 1)
            if playlist_id:
                logger.info(f"Loading tracks from playlist {playlist_id}")
                self._current_playlist_id = playlist_id  # Set current ID
                self._filter_by_playlist(playlist_id)
            else:
                logger.warning("Playlist has no ID")
                self._current_playlist_id = None
        elif item_type == "all_tracks":
            # Show all tracks from library
            self._current_playlist_id = None
            self._current_device_path = None
            self._load_tracks()
            self.status_bar.showMessage("Showing all tracks")
        elif item_type == "root_playlists":
            # Clear table when clicking on Playlists root
            self._current_playlist_id = None
            self._current_device_path = None
            self.table_model.set_tracks([])
            self.status_bar.showMessage("Select a playlist to view tracks")
        elif item_type == "root_library":
            # Show all tracks when clicking Library root
            self._current_playlist_id = None
            self._current_device_path = None
            self._load_tracks()
            self.status_bar.showMessage("Showing all tracks")
        elif item_type == "root_devices":
            # Select root devices
            self._current_playlist_id = None
            self._current_device_path = None
            self.table_model.set_tracks([])
            self.status_bar.showMessage(
                "Select a specific device to view tracks")
        elif item_type == "device":
            # Load tracks from device
            self._current_playlist_id = None
            mount_point = item.data(0, Qt.UserRole + 1)
            self._current_device_path = mount_point
            self._load_device_tracks(mount_point)
        elif item_type == "device_playlist":
            # Load tracks from XML playlist
            self._current_playlist_id = None
            playlist_name = item.data(0, Qt.UserRole + 1)
            self._load_xml_playlist(playlist_name, item)
        elif item_type == "device_playlist_pdb":
            # Load tracks from PDB playlist
            self._current_playlist_id = None
            playlist_id = item.data(0, Qt.UserRole + 1)
            self._load_pdb_playlist(playlist_id, item)

    def _load_xml_playlist(self, playlist_name: str, item):
        """Load tracks from a Rekordbox XML playlist (Volatile)"""
        import xml.etree.ElementTree as ET
        import urllib.parse
        from src.database.models import Track
        
        # Find XML path from parent device
        # Traverse up to find 'device' item
        parent = item.parent()
        while parent and parent.data(0, Qt.UserRole) != "device":
            parent = parent.parent()
            
        if not parent:
            return

        mount_point = parent.data(0, Qt.UserRole + 1)
        if not mount_point:
            return
            
        # Try common XML locations
        mount_path = Path(mount_point)
        xml_candidates = [
            mount_path / "rekordbox.xml",
            mount_path / "PIONEER" / "rekordbox.xml",
            mount_path / "PIONEER" / "Rekordbox" / "rekordbox.xml"
        ]
        
        xml_path = None
        for p in xml_candidates:
            if p.exists():
                xml_path = p
                break
                
        if not xml_path:
            self.status_bar.showMessage("Error: rekordbox.xml not found")
            return
            
        try:
            self.status_bar.showMessage(f"Reading XML Playlist '{playlist_name}'...")
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # 1. Find Playlist Node
            # We search recursively to find the node with Name=playlist_name and Type=1
            target_node = None
            
            playlists_node = root.find('PLAYLISTS')
            if playlists_node:
                # Helper to find node
                queue = [playlists_node]
                while queue:
                    curr = queue.pop(0)
                    for child in curr.findall('NODE'):
                        if child.get('Type') == '1' and child.get('Name') == playlist_name:
                            target_node = child
                            break
                        elif child.get('Type') == '0': # Folder
                            queue.append(child)
                    if target_node: break
            
            if not target_node:
                self.status_bar.showMessage(f"Playlist '{playlist_name}' not found in XML")
                return
                
            # 2. Collect Track IDs
            track_keys = set()
            for t_node in target_node.findall('TRACK'):
                key = t_node.get('Key')
                if key: track_keys.add(key)
                
            if not track_keys:
                self.table_model.set_tracks([])
                self.status_bar.showMessage("Playlist is empty")
                return
                
            # 3. Parse Collection to get Track Details
            ui_tracks = []
            collection = root.find('COLLECTION')
            if collection:
                for track_node in collection.findall('TRACK'):
                    tid = track_node.get('TrackID')
                    if tid in track_keys:
                        # Extract metadata
                        name = track_node.get('Name', 'Unknown')
                        artist = track_node.get('Artist', 'Unknown')
                        bpm = float(track_node.get('AverageBpm', 0))
                        
                        location = track_node.get('Location', '')
                        file_path = ""
                        
                        if location:
                            # Parse URL
                            parsed = urllib.parse.urlparse(location)
                            decoded_path = urllib.parse.unquote(parsed.path)
                            
                            # Fix path if needed (e.g. localhost/Y/...)
                            # Usually extracts to /Y/PIONEER...
                            # We need to map it to mount_point
                            
                            # Simple heuristic: If path starts with /Y/ or similar drive letter pattern
                            # strip it and prepend mount_point?
                            # Or reconstruct from mount_point contents
                            
                            # But wait, generated XML has 'file://localhostY/PIONEER...' (missing slash?)
                            # Generated path: 'file://localhost' + 'Y/PIONEER...'
                            # urllib path might remain 'Y/PIONEER...'
                            
                            file_path = decoded_path
                            
                        t = Track(
                            title=name,
                            artist=artist,
                            file_path=file_path,
                            bpm=bpm
                        )
                        t.id = tid # Use XML ID locally
                        ui_tracks.append(t)
            
            self.table_model.set_tracks(ui_tracks)
            self.status_bar.showMessage(f"Loaded {len(ui_tracks)} tracks from XML")
            logger.info(f"Loaded {len(ui_tracks)} tracks for playlist '{playlist_name}'")

        except Exception as e:
            logger.error(f"Error loading XML playlist: {e}")
            self.status_bar.showMessage("Error reading XML")
        """Load tracks from a Rekordbox PDB playlist"""
        from src.importer.pdb_importer import DeviceSqlImporter
        from src.database.models import Track
        import os
        from pathlib import Path

        # Find mount point from parent device item
        parent = item.parent()
        if not parent:
            return
        mount_point = parent.data(0, Qt.UserRole + 1)
        if not mount_point:
            return

        pdb_path = Path(mount_point) / "PIONEER" / "Rekordbox" / "export.pdb"
        if not pdb_path.exists():
            self.status_bar.showMessage("Error: export.pdb not found")
            return

        try:
            self.status_bar.showMessage(
                f"Reading PDB Playlist {playlist_id}...")
            importer = DeviceSqlImporter()
            if importer.open(str(pdb_path)):
                # Fetch raw track data
                raw_tracks = importer.get_playlist_tracks(playlist_id)
                importer.close()

                # Convert to UI Track objects
                ui_tracks = []
                for rt in raw_tracks:
                    title = rt.get('title', 'Unknown Track')
                    artist = rt.get('artist', 'Unknown Artist')
                    bpm = rt.get('bpm', 0.0)
                    pdb_rpath = rt.get('path', '')

                    real_path = ""
                    if pdb_rpath:
                        # Clean path: Remove "Y/" or "A/" prefix
                        # e.g. Y/PIONEER/Music/Song.mp3 -> PIONEER/Music/Song.mp3
                        parts = pdb_rpath.split('/', 1)
                        # Drive letter check
                        if len(parts) > 1 and len(parts[0]) <= 2:
                            clean_rpath = parts[1]
                        else:
                            clean_rpath = pdb_rpath

                        # Try to find file
                        candidate = Path(mount_point) / clean_rpath
                        if candidate.exists():
                            real_path = str(candidate)
                        else:
                            # Fallback: try searching in PIONEER folder if relative path is weird
                            pass

                    t = Track(
                        title=title,
                        artist=artist,
                        file_path=real_path
                    )
                    t.id = rt.get('id')  # Internal PDB ID
                    t.bpm = bpm

                    ui_tracks.append(t)

                self.table_model.set_tracks(ui_tracks)
                self.status_bar.showMessage(
                    f"Loaded {len(ui_tracks)} tracks from PDB")
                logger.info(
                    f"Loaded {len(ui_tracks)} from PDB Playlist {playlist_id}")
            else:
                self.status_bar.showMessage("Failed to open PDB database")

        except Exception as e:
            logger.error(f"Error reading PDB playlist: {e}")
            self.status_bar.showMessage("Error reading playlist")

    def _load_device_tracks(self, mount_point: str):
        """Load tracks from a device directory"""
        if not mount_point:
            return

        if self._is_loading_device:
            logger.warning(
                "Already loading device tracks, skipping re-entrant call")
            return

        self._is_loading_device = True

        from pathlib import Path
        import os
        from src.database.models import Track

        try:
            self.status_bar.showMessage(f"Scanning device: {mount_point}...")
            # Ideally this should run in a thread, but for now we optimize the query

            self.table_model.set_tracks([])

            # extensions to look for
            valid_exts = {'.wav', '.mp3', '.aiff',
                          '.aif', '.flac', '.m4a', '.aac'}
            found_tracks = []

            # 1. Walk directory to find files
            device_files = []
            file_paths_to_check = []

            for root, dirs, files in os.walk(mount_point):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in valid_exts:
                        full_path = str(Path(root) / file)
                        device_files.append((file, full_path, root))
                        file_paths_to_check.append(full_path)

            # 2. Batch match with DB
            # Use get_by_paths to fetch all known tracks in one query
            existing_tracks_map = self.repository.get_by_paths(
                file_paths_to_check)

            for fname, fpath, froot in device_files:
                # Check Local Map
                existing = existing_tracks_map.get(fpath)

                if existing:
                    found_tracks.append(existing)
                else:
                    # Create temporary track object
                    track = Track(
                        title=fname,  # Use filename as title initially
                        file_path=fpath,
                        artist="External",
                        album=self._get_parent_folder_name(froot)
                    )
                    # Set a temporary ID
                    track.id = None
                    # Ensure None values for critical fields to avoid attribute errors
                    track.bpm = 0.0
                    track.key_camelot = ""
                    track.rating = 0
                    track.duration_seconds = 0
                    track.artwork_thumbnail = None
                    found_tracks.append(track)

            self.table_model.set_tracks(found_tracks)
            self.status_bar.showMessage(
                f"Found {len(found_tracks)} tracks on device")
            logger.info(
                f"Loaded {len(found_tracks)} tracks from device {mount_point}")

        except Exception as e:
            logger.error(f"Error loading device tracks: {e}")
            self.status_bar.showMessage(f"Error loading tracks: {str(e)}")
        finally:
            self._is_loading_device = False

    def _get_parent_folder_name(self, path):
        import os
        return os.path.basename(path)

    def _filter_by_playlist(self, playlist_id: int):
        """Filter table to show only tracks from a specific playlist"""
        from src.database.repository import PlaylistRepository

        # Get tracks for this playlist
        tracks = PlaylistRepository.get_tracks(playlist_id)

        if tracks:
            self.table_model.set_tracks(tracks)
            self.status_bar.showMessage(
                f"Showing {len(tracks)} tracks from playlist")
            logger.info(
                f"Loaded {len(tracks)} tracks from playlist {playlist_id}")
        else:
            self.table_model.set_tracks([])
            self.status_bar.showMessage("No tracks in this playlist")

    def _on_playlist_created(self, name: str):
        """Handle playlist creation"""
        from src.database.repository import PlaylistRepository

        playlist = PlaylistRepository.create(name)
        if playlist:
            logger.info(f"Playlist '{name}' created with ID {playlist.id}")
        else:
            logger.error(f"Failed to create playlist '{name}'")

    def _load_playlists(self):
        """Load playlists from database into sidebar"""
        try:
            playlists = PlaylistRepository.get_all()
            logger.info(f"Loading {len(playlists)} playlists")
            for playlist in playlists:
                self.sidebar.add_playlist(playlist.name, playlist.id)
        except Exception as e:
            logger.error(f"Error loading playlists: {e}")

    def _populate_playlist_menu(self, menu, track_ids):
        """Populate playlist submenu with available playlists"""
        from src.database.repository import PlaylistRepository

        playlists = PlaylistRepository.get_all()

        if not playlists:
            menu.addAction("No playlists available").setEnabled(False)
            return

        for playlist in playlists:
            action = menu.addAction(f"📁 {playlist.name}")
            # Use lambda with default argument to capture current playlist
            action.triggered.connect(
                lambda checked=False, p=playlist, t=track_ids: self._add_tracks_to_playlist(p.id, t))

    def _add_tracks_to_playlist(self, playlist_id: int, track_ids: list):
        """Add tracks to a playlist"""
        from src.database.repository import PlaylistRepository

        added_count = 0
        for track_id in track_ids:
            if PlaylistRepository.add_track(playlist_id, track_id):
                added_count += 1

        if added_count > 0:
            logger.info(
                f"Added {added_count} tracks to playlist {playlist_id}")
            self.status_bar.showMessage(
                f"Added {added_count} track(s) to playlist")
        else:
            logger.warning(f"Failed to add tracks to playlist {playlist_id}")

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Track count label
        self.track_count_label = QLabel("0 tracks")
        self.status_bar.addPermanentWidget(self.track_count_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_bar.showMessage("Ready")

    def _load_tracks(self):
        """Load tracks from database"""
        try:
            tracks = self.repository.get_all()
            self.table_model.set_tracks(tracks)
            self.track_count_label.setText(f"{len(tracks)} tracks")
            self.status_bar.showMessage(f"Loaded {len(tracks)} tracks")
            logger.info(f"Loaded {len(tracks)} tracks")
        except Exception as e:
            logger.error(f"Error loading tracks: {e}")
            QMessageBox.critical(
                self, "Error", f"Failed to load tracks:\n{str(e)}")

    def _on_files_dropped(self, file_paths: list):
        """Handle dropped files"""
        self._import_tracks_metadata(file_paths)

    def _import_files(self):
        """Import files dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Audio Files",
            "",
            "Audio Files (*.flac *.aiff *.wav *.mp3 *.m4a)"
        )

        if files:
            self._import_tracks_metadata(files)

    def _import_folder(self):
        """Import folder dialog"""
        folder = QFileDialog.getExistingDirectory(self, "Import Folder")

        if folder:
            # Scan for audio files
            path = Path(folder)
            files = []
            for ext in ['.flac', '.aiff', '.wav', '.mp3', '.m4a']:
                files.extend([str(p) for p in path.rglob(f'*{ext}')])

            if files:
                self._import_tracks_metadata(files)
            else:
                QMessageBox.information(
                    self, "No Files", "No audio files found in folder")

    def _import_tracks_metadata(self, file_paths: list):
        """Import tracks metadata (fast) without analysis"""
        imported_count = 0
        self.status_bar.showMessage(f"Importing {len(file_paths)} files...")

        # Filter keys logic (reused)
        from src.database.models import Track
        valid_keys = {c.name for c in Track.__table__.columns}

        for file_path in file_paths:
            try:
                # Check if already exists
                existing = self.repository.get_by_path(file_path)
                if existing:
                    continue

                # Get basic audio info
                audio_info = self.audio_processor.get_audio_info(file_path)
                audio_info.pop('channels', None)
                audio_info.pop('subtype', None)

                # Create track data
                track_data = {
                    'title': Path(file_path).stem,
                    'file_path': file_path,
                    'artist': 'Unknown Artist',  # TODO: Extract from tags if available
                    **audio_info
                }

                # Filter keys
                track_data = {k: v for k, v in track_data.items()
                              if k in valid_keys}

                # Create track
                track = self.repository.create(track_data)
                if track:
                    self.table_model.add_track(track)
                    imported_count += 1

            except Exception as e:
                logger.error(f"Error importing {file_path}: {e}")

        self.status_bar.showMessage(f"Imported {imported_count} new tracks")

    def _import_files_generic(self, file_paths: list, target_playlist_id: int = None):
        """Generic import logic used by all import methods"""
        from src.database.models import Track

        valid_extensions = {'.mp3', '.wav', '.aiff', '.flac', '.m4a'}
        valid_files = [f for f in file_paths if Path(
            f).suffix.lower() in valid_extensions]

        if not valid_files:
            return

        imported_count = 0
        added_to_playlist_count = 0
        imported_ids = []

        # Valid keys for Track model
        valid_keys = {c.name for c in Track.__table__.columns}

        for file_path in valid_files:
            try:
                # Validate file security
                try:
                    validate_audio_file(file_path)
                except ValueError as e:
                    logger.warning(f"Skipping invalid file {file_path}: {e}")
                    continue

                # Check if already exists
                existing = self.repository.get_by_path(file_path)
                track_id = None

                if existing:
                    track_id = existing.id
                else:
                    # Get basic audio info
                    audio_info = self.audio_processor.get_audio_info(file_path)
                    audio_info.pop('channels', None)
                    audio_info.pop('subtype', None)

                    # Create track data
                    track_data = {
                        'title': Path(file_path).stem,
                        'file_path': file_path,
                        'artist': 'Unknown Artist',
                        **audio_info
                    }

                    # Extract artwork
                    artwork = self.audio_processor.extract_artwork(file_path)
                    if artwork:
                        track_data['artwork_thumbnail'] = artwork

                    # Filter keys
                    track_data = {k: v for k,
                                  v in track_data.items() if k in valid_keys}

                    # Create track
                    track = self.repository.create(track_data)
                    if track:
                        self.table_model.add_track(track)
                        track_id = track.id
                        imported_count += 1

                if track_id:
                    imported_ids.append(track_id)
                    # Add to target playlist if specified
                    if target_playlist_id:
                        if PlaylistRepository.add_track(target_playlist_id, track_id):
                            added_to_playlist_count += 1

            except Exception as e:
                logger.error(f"Error importing {file_path}: {e}")

        # Refresh UI if added to CURRENT playlist
        if target_playlist_id and self._current_playlist_id == target_playlist_id:
            self._load_tracks(playlist_id=target_playlist_id)
        else:
            self.track_count_label.setText(
                f"{self.table_model.rowCount()} tracks")

        msg = f"Processed {len(valid_files)} files."
        if imported_count > 0:
            msg += f" Imported {imported_count} new."
        if added_to_playlist_count > 0:
            msg += f" Added {added_to_playlist_count} to playlist."

        self.status_bar.showMessage(msg)

    def _import_files(self):
        """Import audio files via dialog"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Audio Files",
            str(Path.home()),
            "Audio Files (*.mp3 *.wav *.aiff *.flac *.m4a)"
        )
        if file_paths:
            self._import_files_generic(file_paths)

    def _import_folder(self):
        """Import audio files from folder"""
        folder_path = QFileDialog.getExistingDirectory(self, "Import Folder")
        if folder_path:
            file_paths = []
            for ext in ['*.mp3', '*.wav', '*.aiff', '*.flac', '*.m4a']:
                file_paths.extend([str(p)
                                  for p in Path(folder_path).rglob(ext)])

            if file_paths:
                self._import_files_generic(file_paths)

    def _import_from_rekordbox(self):
        """Import tracks and playlists from Rekordbox XML"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Rekordbox XML",
            "",
            "Rekordbox XML (*.xml)"
        )

        if file_path:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import Qt

            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.status_bar.showMessage(
                f"Importing Rekordbox XML: {file_path}...")

            try:
                importer = RekordboxImporter()
                tracks_count, playlists_count = importer.parse_xml(file_path)

                self.sidebar.reload_playlists()
                self._load_tracks()  # Refresh library

                QMessageBox.information(self, "Import Successful",
                                        f"Imported {tracks_count} tracks and {playlists_count} playlists from Rekordbox XML.")
            except Exception as e:
                logger.error(f"Rekordbox import failed: {e}")
                QMessageBox.critical(self, "Import Error",
                                     f"Failed to import Rekordbox XML: {e}")
            finally:
                QApplication.restoreOverrideCursor()
                self.status_bar.showMessage("Ready")

    def _import_dropped_files(self, file_paths):
        """Handle dropped files"""
        self._import_files_generic(
            file_paths, target_playlist_id=self._current_playlist_id)

    def _add_tracks_to_playlist_dialog(self, playlist_id):
        """Add tracks to playlist from files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Tracks to Playlist",
            str(Path.home()),
            "Audio Files (*.mp3 *.wav *.aiff *.flac *.m4a)"
        )
        if file_paths:
            self._import_files_generic(
                file_paths, target_playlist_id=playlist_id)

    def _start_analysis(self, file_paths: list):
        """Start analysis worker"""
        if self.analysis_worker and self.analysis_worker.isRunning():
            QMessageBox.warning(self, "Analysis Running",
                                "Please wait for current analysis to finish")
            return

        self.status_bar.showMessage(f"Analyzing {len(file_paths)} files...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(file_paths))
        self.progress_bar.setValue(0)

        self.analysis_worker = AnalysisWorker(file_paths)
        self.analysis_worker.progress.connect(self._on_analysis_progress)
        self.analysis_worker.track_analyzed.connect(self._on_track_analyzed)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)
        self.analysis_worker.start()

    def _on_analysis_progress(self, current: int, total: int):
        """Update progress"""
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Analyzing... {current}/{total}")

    def _on_track_analyzed(self, file_path: str, analysis):
        """Handle analyzed track"""
        from datetime import datetime

        try:
            # Check if track exists
            existing_track = self.repository.get_by_path(file_path)

            # Prepare analysis data
            analysis_data = {
                'key_camelot': analysis.key_camelot,
                'key_musical': analysis.key_musical,
                'bpm': analysis.bpm,
                'energy_level': analysis.energy_level,
                'duration_seconds': analysis.duration_seconds,
                'waveform_data': self.audio_processor.waveform_to_bytes(analysis.waveform_data),
                'analyzed_at': datetime.utcnow()
            }

            # Add artwork if available from analysis
            if hasattr(analysis, 'artwork') and analysis.artwork:
                analysis_data['artwork_thumbnail'] = analysis.artwork

            if existing_track:
                # Update existing track
                updated_track = self.repository.update(
                    existing_track.id, analysis_data)
                if updated_track:
                    # Update model (trickier, need to find row or reload)
                    # For now we can reload the specific row or all
                    # Ideally TableModel has an update method
                    self.table_model.update_track(updated_track)
            else:
                # Create new (fallback if analysis run on non-imported file)
                audio_info = self.audio_processor.get_audio_info(file_path)
                audio_info.pop('channels', None)
                audio_info.pop('subtype', None)

                track_data = {
                    'title': Path(file_path).stem,
                    'file_path': file_path,
                    **analysis_data,
                    **audio_info
                }

                # Filter keys
                from src.database.models import Track
                valid_keys = {c.name for c in Track.__table__.columns}
                track_data = {k: v for k, v in track_data.items()
                              if k in valid_keys}

                track = self.repository.create(track_data)
                if track:
                    self.table_model.add_track(track)

            self.track_count_label.setText(
                f"{self.table_model.rowCount()} tracks")

        except Exception as e:
            logger.error(f"Error saving track {file_path}: {e}")

    def _on_analysis_finished(self):
        """Analysis finished"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Analysis complete", 3000)
        # Removed redundant QMessageBox to avoid "two windows" complaint

    def _on_analysis_error(self, error: str):
        """Analysis error"""
        logger.error(f"Analysis error: {error}")
        self.status_bar.showMessage(f"Error: {error}", 5000)

    # ==========================
    # Transcode Workflow
    # ==========================

    def _on_transcode_requested(self, track_ids: list, target_format: str = 'aiff'):
        """Handle transcode request"""
        if not track_ids:
            return

        # Select Output Directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory")
        if not output_dir:
            return

        # Prepare files
        track_files = {}
        for track_id in track_ids:
            track = self.repository.get_by_id(track_id)
            if track and track.file_path:
                track_files[track.id] = track.file_path

        if not track_files:
            return

        # Start Worker
        self.transcode_worker = TranscodeWorker(
            track_files, output_dir, target_format)
        self.transcode_worker.progress.connect(self._on_transcode_progress)
        self.transcode_worker.finished.connect(self._on_transcode_finished)
        self.transcode_worker.file_transcoded.connect(self._on_file_transcoded)
        self.transcode_worker.error.connect(self._on_analysis_error)

        self.status_bar.showMessage(
            f"Transcoding {len(track_files)} tracks to {target_format.upper()}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(track_files))
        self.progress_bar.setValue(0)

        # Reset tracking list
        self.transcoded_results = []  # List of new file paths

        self.transcode_worker.start()

    def _on_transcode_playlist_requested(self, playlist_id: int, target_format: str):
        """Handle transcode request for entire playlist"""
        # Get all tracks in playlist
        from src.database.repository import PlaylistRepository
        tracks = PlaylistRepository.get_tracks(playlist_id)

        if not tracks:
            QMessageBox.information(
                self, "Empty Playlist", "This playlist has no tracks to transcode.")
            return

        track_ids = [t.id for t in tracks]
        self._on_transcode_requested(track_ids, target_format)

    def _on_transcode_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Transcoding: {current}/{total}")

    def _on_file_transcoded(self, original_id, new_path):
        self.transcoded_results.append(new_path)
        logger.info(f"Transcoded: {new_path}")

    def _on_transcode_finished(self):
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(
            f"Transcoding complete. {len(self.transcoded_results)} files created.", 5000)

        if not self.transcoded_results:
            return

        # Check if we are viewing the output folder in Devices
        if self._current_device_path:
            # Check if any new file is in current path
            should_refresh = False
            for new_path in self.transcoded_results:
                if str(Path(new_path).parent).startswith(self._current_device_path):
                    should_refresh = True
                    break

            if should_refresh:
                self._load_device_tracks(self._current_device_path)
                QMessageBox.information(
                    self, "Refreshed", f"Found {len(self.transcoded_results)} new files in current folder.")

        # Ask to create playlist
        from PySide6.QtWidgets import QMessageBox as QMsgBox, QInputDialog
        reply = QMsgBox.question(self, "Transcoding Complete",
                                 f"Successfully converted {len(self.transcoded_results)} tracks.\n\n"
                                 "Do you want to create a new playlist with these tracks?",
                                 QMsgBox.Yes | QMsgBox.No)

        if reply == QMsgBox.Yes:
            from datetime import datetime
            default_name = f"Transcoded {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            name, ok = QInputDialog.getText(
                self, "New Playlist", "Playlist Name:", text=default_name)

            if ok and name:
                playlist = self._import_transcoded_to_playlist(
                    name, self.transcoded_results)

                if playlist:
                    xml_reply = QMsgBox.question(self, "Export Rekordbox XML",
                                                 "Do you also want to generate a 'rekordbox.xml' in the destination folder?\n(Recommended for USB exports)",
                                                 QMsgBox.Yes | QMsgBox.No)
                    if xml_reply == QMsgBox.Yes:
                        try:
                            from src.export.rekordbox_exporter import RekordboxExporter
                            from src.database.repository import PlaylistRepository

                            exporter = RekordboxExporter()
                            tracks = PlaylistRepository.get_tracks(playlist.id)
                            output_dir = Path(
                                self.transcoded_results[0]).parent
                            xml_path = output_dir / "rekordbox.xml"

                            if exporter.export_playlist(tracks, playlist.name, str(xml_path)):
                                QMsgBox.information(
                                    self, "Export Complete", f"Generated: {xml_path}")
                        except Exception as e:
                            logger.error(f"XML Export error: {e}")
                            QMsgBox.warning(self, "Export Failed", str(e))

    def _import_transcoded_to_playlist(self, playlist_name, file_paths):
        """Import transcoded files and add to playlist"""
        # 1. Create Playlist
        playlist = PlaylistRepository.create(playlist_name)
        if not playlist:
            QMessageBox.critical(self, "Error", "Failed to create playlist")
            return

        added_ids = []
        for path in file_paths:
            # Check if already exists
            existing = self.repository.get_by_path(path)
            if existing:
                added_ids.append(existing.id)
            else:
                try:
                    track_data = {
                        'title': Path(path).stem,
                        'file_path': path,
                        'bpm': 0, 'energy_level': 0, 'key_camelot': '', 'duration_seconds': 0
                    }
                    # Filter keys
                    from src.database.models import Track
                    valid_keys = {c.name for c in Track.__table__.columns}
                    track_data = {k: v for k,
                                  v in track_data.items() if k in valid_keys}

                    new_track = self.repository.create(track_data)
                    if new_track:
                        added_ids.append(new_track.id)
                        self.table_model.add_track(new_track)
                except Exception as e:
                    logger.error(f"Error creating track for {path}: {e}")

        # 3. Add to Playlist
        count = 0
        for tid in added_ids:
            if PlaylistRepository.add_track(playlist.id, tid):
                count += 1

        # 4. Refresh Sidebar
        self.sidebar.reload_playlists()

        # 5. Trigger Analysis (Background)
        if added_ids:
            self._start_analysis([path for path in file_paths])

        QMessageBox.information(
            self, "Success", f"Created playlist '{playlist_name}' with {count} tracks.")
        return playlist

    def _on_track_double_clicked(self, track_id: int):
        """Load track waveform"""
        logger.info(f"Double-clicked track ID: {track_id}")
        track = self.repository.get_by_id(track_id)

        if not track:
            logger.warning(f"Track {track_id} not found")
            return

        if track:
            self.deck_a.load_track(track)
            self.status_bar.showMessage(f"Loaded: {track.title}")

    def _on_selection_changed(self, selected, deselected):
        """Handle selection change"""
        # We don't want to auto-load on selection as it interferes with drag and drop
        # and is bad UX. Loading should be explicit (drag or double click).
        pass

    def _load_track(self, track_id: int, deck_id: str):
        """Load track by ID into specific deck"""
        track = self.repository.get_by_id(track_id)
        if not track:
            logger.error(f"Track {track_id} not found")
            return

        target_deck = self.deck_a if deck_id == "A" else self.deck_b
        target_deck.load_track(track)

        # Determine color based on deck
        color = "#00E5FF" if deck_id == "A" else "#FF4081"
        self.status_bar.showMessage(f"Loaded {track.title} to Deck {deck_id}")

    def _load_to_deck(self, deck_widget):
        """Load currently selected track to deck"""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        track = self.table_model.get_track(row)
        if track:
            deck_widget.load_track(track)
            self.status_bar.showMessage(
                f"Loaded {track.title} to Deck {deck_widget.deck_id}")

    def _on_table_double_clicked(self, index):
        """Handle double click on table - Load to Deck A"""
        if not index.isValid():
            return

        row = index.row()
        track = self.table_model.get_track(row)

        if track:
            self.deck_a.load_track(track)
            self.status_bar.showMessage(f"Loaded {track.title} to Deck A")

    def _load_to_deck_a(self):
        """Load selected track to Deck A"""
        self._load_to_deck(self.deck_a)

    def _load_to_deck_b(self):
        """Load selected track to Deck B"""
        self._load_to_deck(self.deck_b)

    def _load_to_deck(self, deck):
        """Load selected track to specified deck"""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        track = self.table_model.get_track(row)

        if track:
            # Check if we need to fetch full object
            if not track.waveform_data and track.id:
                # Try to fetch from DB to get waveform
                full_track = self.repository.get_by_id(track.id)
                if full_track:
                    track = full_track

            deck.load_track(track)
            logger.info(f"Loaded track to Deck {deck.deck_id}: {track.title}")

    def _analyze_selected_tracks(self):
        """Analyze currently selected tracks"""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        track_ids = []
        for index in indexes:
            row = index.row()
            track = self.table_model.get_track(row)
            if track and track.id:
                track_ids.append(track.id)

        if track_ids:
            self._on_analyze_requested(track_ids)

    def _on_analyze_requested(self, track_ids: list):
        """Re-analyze tracks"""
        logger.info(
            f"Analysis requested for {len(track_ids)} tracks: {track_ids}")

        # Get file paths
        file_paths = []
        for track_id in track_ids:
            track = self.repository.get_by_id(track_id)
            if track:
                file_paths.append(track.file_path)
                logger.info(f"Found track {track_id}: {track.file_path}")
            else:
                logger.warning(f"Track {track_id} not found in database")

        logger.info(f"Starting analysis for {len(file_paths)} file paths")
        if file_paths:
            self._start_analysis(file_paths)
        else:
            logger.error("No file paths found for analysis")

    def _on_delete_requested(self, track_ids: list):
        """Handle delete request with advanced options"""
        if not track_ids:
            return

        count = len(track_ids)

        # Create custom dialog
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox
        import os

        dialog = QDialog(self)
        dialog.setWindowTitle("Remove Tracks")
        layout = QVBoxLayout(dialog)

        # Message
        if self._current_playlist_id:
            msg = f"Remove {count} tracks from this playlist?"
        else:
            msg = f"Remove {count} tracks from Library?"
        layout.addWidget(QLabel(msg))

        # Options
        check_delete_library = None
        if self._current_playlist_id:
            check_delete_library = QCheckBox(
                "Also remove from Library (Database)")
            layout.addWidget(check_delete_library)

        check_delete_disk = QCheckBox(
            "⚠️ Also delete files from DISK (Permanent)")
        # Style filtering for danger
        check_delete_disk.setStyleSheet("color: #ff5555; font-weight: bold;")
        layout.addWidget(check_delete_disk)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        # Dynamic behavior: checking disk automatically checks library
        if check_delete_library:
            check_delete_disk.toggled.connect(
                lambda checked: check_delete_library.setChecked(True) if checked else None)

        if dialog.exec_() != QDialog.Accepted:
            return

        # Execute actions
        delete_from_lib = True  # Default for library view

        if self._current_playlist_id:
            # First remove from playlist
            from src.database.repository import PlaylistRepository
            for t_id in track_ids:
                PlaylistRepository.remove_track(
                    self._current_playlist_id, t_id)

            # Determine if we continue to library delete
            if check_delete_library and not check_delete_library.isChecked():
                delete_from_lib = False

        if delete_from_lib:
            # Collect file paths BEFORE deleting from DB
            files_to_delete = []
            if check_delete_disk.isChecked():
                for t_id in track_ids:
                    track = self.repository.get_by_id(t_id)
                    if track and track.file_path:
                        files_to_delete.append(track.file_path)

            # Delete from DB
            for t_id in track_ids:
                self.repository.delete(t_id)

            # Delete from Disk
            if check_delete_disk.isChecked():
                deleted_files = 0
                for fp in files_to_delete:
                    try:
                        if os.path.exists(fp):
                            os.remove(fp)
                            deleted_files += 1
                            logger.info(f"Deleted file: {fp}")
                    except Exception as e:
                        logger.error(f"Error deleting file {fp}: {e}")

                if deleted_files > 0:
                    self.status_bar.showMessage(
                        f"Removed {count} tracks and {deleted_files} files from disk", 4000)
                else:
                    self.status_bar.showMessage(
                        f"Removed {count} tracks from library", 3000)
            else:
                self.status_bar.showMessage(
                    f"Removed {count} tracks from library", 3000)
        else:
            self.status_bar.showMessage(
                f"Removed {count} tracks from playlist", 3000)

        # Refresh UI
        if self._current_playlist_id:
            self._filter_by_playlist(self._current_playlist_id)
        else:
            self._load_tracks()

    def _on_export_requested(self, track_ids: list):
        """Export tracks to Rekordbox"""
        self._export_to_rekordbox(track_ids)

    def _export_to_rekordbox(self, track_ids: list = None):
        """Export to Rekordbox XML"""
        # Get tracks
        if track_ids:
            tracks = [self.repository.get_by_id(tid) for tid in track_ids]
            tracks = [t for t in tracks if t is not None]
        else:
            tracks = self.repository.get_all()

        if not tracks:
            QMessageBox.information(self, "No Tracks", "No tracks to export")
            return

        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Rekordbox",
            "rekordbox.xml",
            "XML Files (*.xml)"
        )

        if file_path:
            try:
                if self.exporter.export_library(tracks, file_path):
                    QMessageBox.information(
                        self,
                        "Export Complete",
                        f"Exported {len(tracks)} tracks to:\n{file_path}"
                    )
                else:
                    QMessageBox.critical(
                        self, "Export Failed", "Failed to export tracks")
            except Exception as e:
                logger.error(f"Export error: {e}")
                QMessageBox.critical(
                    self, "Error", f"Export failed:\n{str(e)}")

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About ToneMix Pro",
            "<h2>ToneMix Pro v0.1.0</h2>"
            "<p>Professional Music Analysis Software</p>"
            "<p>Open source MIR tool for DJs</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Key detection (Camelot Wheel)</li>"
            "<li>BPM analysis</li>"
            "<li>Energy level calculation</li>"
            "<li>Waveform visualization</li>"
            "<li>Rekordbox export</li>"
            "</ul>"
            "<p><a href='https://github.com/esfingex/tonemix'>GitHub Repository</a></p>"
        )

    def _show_preferences(self):
        """Show preferences dialog"""
        dialog = PreferencesDialog(self)

        # Connect signals
        dialog.preferences_changed.connect(self._on_preferences_changed)
        dialog.shortcuts_changed.connect(self._on_shortcuts_changed)
        dialog.exec_()

    def _on_preferences_changed(self, prefs):
        """Handle preference changes"""
        # Save to config if needed or handled by generic saving
        pass

        # Apply to decks
        if hasattr(self, 'deck_a'):
            self.deck_a.waveform.set_preferences(prefs)
        if hasattr(self, 'deck_b'):
            self.deck_b.waveform.set_preferences(prefs)

        logger.info(f"Preferences applied: {prefs}")

    def _on_shortcuts_changed(self, shortcuts):
        """Handle shortcuts update"""
        # Config already saved by Dialog
        self._setup_shortcuts()
        logger.info("Shortcuts updated")

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Clear existing
        for s in self._shortcuts:
            s.setEnabled(False)
            s.setParent(None)
        self._shortcuts.clear()

        # Get config
        shortcuts = config.shortcuts

        # Migration: Fix Ctrl+A conflict for existing users
        if shortcuts.get('analyze_selected') == 'Ctrl+A':
            logger.info(
                "Migrating shortcut: analyze_selected Ctrl+A -> Ctrl+Shift+A")
            shortcuts['analyze_selected'] = 'Ctrl+Shift+A'
            shortcuts['select_all'] = 'Ctrl+A'
            config.set('shortcuts', shortcuts)
            config.save()

        defaults = {
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

        # Merge
        active_shortcuts = defaults.copy()
        active_shortcuts.update(shortcuts)

        # Map IDs to methods
        actions = {
            "play_deck_a": lambda: self.deck_a.play_pause() if hasattr(self, 'deck_a') else None,
            "play_deck_b": lambda: self.deck_b.play_pause() if hasattr(self, 'deck_b') else None,
            "cue_deck_a": lambda: self.deck_a.cue_track() if hasattr(self, 'deck_a') else None,
            "cue_deck_b": lambda: self.deck_b.cue_track() if hasattr(self, 'deck_b') else None,
            "load_deck_a": self._load_to_deck_a,
            "load_deck_b": self._load_to_deck_b,
            "delete_from_playlist": self._on_delete_requested_shortcut,
            "analyze_selected": self._analyze_selected_tracks_shortcut,
            "transcode_selected": self._transcode_selected_shortcut,
            "select_all": lambda: self.table_view.selectAll() if hasattr(self, 'table_view') else None
        }

        for action_id, key_seq in active_shortcuts.items():
            if not key_seq:
                continue

            if action_id in actions:
                shortcut = QShortcut(QKeySequence(key_seq), self)
                shortcut.activated.connect(actions[action_id])
                self._shortcuts.append(shortcut)

    def _on_delete_requested_shortcut(self):
        # Trigger delete on table selection
        ids = self.table_view.get_selected_track_ids()
        if ids:
            self._on_delete_requested(ids)

    def _transcode_selected_shortcut(self):
        ids = self.table_view.get_selected_track_ids()
        if ids:
            self._on_transcode_requested(ids)

    def _analyze_selected_tracks_shortcut(self):
        ids = self.table_view.get_selected_track_ids()
        if ids:
            self._on_analyze_requested(ids)

    def _restore_settings(self):
        """Restore UI settings from previous session"""
        from PySide6.QtCore import QSettings

        settings = QSettings("ToneMix", "ToneMixPro")

        # Window geometry
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Sidebar visibility
        sidebar_visible = settings.value("sidebar/visible", True, type=bool)
        self.sidebar.setVisible(sidebar_visible)
        self.toggle_sidebar_action.setChecked(sidebar_visible)

        # Splitter sizes
        splitter_sizes = settings.value("splitter/sizes")
        if splitter_sizes:
            self.main_splitter.setSizes([int(s) for s in splitter_sizes])

        # Column visibility
        header = self.table_view.horizontalHeader()
        for col in range(self.table_model.columnCount()):
            hidden = settings.value(f"columns/hidden_{col}", False, type=bool)
            header.setSectionHidden(col, hidden)

        logger.info("Settings restored")

    def _save_settings(self):
        """Save UI settings for next session"""
        from PySide6.QtCore import QSettings

        settings = QSettings("ToneMix", "ToneMixPro")

        # Window geometry
        settings.setValue("window/geometry", self.saveGeometry())

        # Sidebar visibility
        settings.setValue("sidebar/visible", self.sidebar.isVisible())

        # Splitter sizes
        settings.setValue("splitter/sizes", self.main_splitter.sizes())

        # Column visibility
        header = self.table_view.horizontalHeader()
        for col in range(self.table_model.columnCount()):
            settings.setValue(
                f"columns/hidden_{col}", header.isSectionHidden(col))

        logger.info("Settings saved")

    def closeEvent(self, event):
        """Handle window close - save settings"""
        self._save_settings()
        event.accept()
