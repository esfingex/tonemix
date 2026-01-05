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
from src.ui.widgets.table_view import LibraryTableView
from src.ui.widgets.sidebar import Sidebar
from src.ui.widgets.audio_player import AudioPlayer
# from src.ui.widgets.drop_zone import DropZone
from src.ui.models import TrackTableModel, Track
from src.database.repository import TrackRepository, PlaylistRepository
from src.core.analyzer import AudioAnalyzer
from src.core.audio_processor import AudioProcessor
from src.export.rekordbox_exporter import RekordboxExporter
from src.ui.dialogs.waveform_preferences import WaveformPreferencesDialog

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
            max_workers = max(1, os.cpu_count() - 1) # Leave one core free for UI
            
            logger.info(f"Starting parallel analysis with {max_workers} workers")
            
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Map file paths to futures
                file_map = {executor.submit(run_single_analysis, fp): fp for fp in self.file_paths}
                
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
                        self.error.emit(f"Error analyzing {Path(file_path).name}: {str(e)}")
            
            self.finished.emit()
            
        except Exception as e:
            logger.error(f"Analysis worker error: {e}")
            self.error.emit(str(e))


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
        
        # Analysis worker
        self.analysis_worker = None
        
        # Setup UI
        self._create_menu_bar()
        self._create_toolbar()
        self._create_ui()
        self._create_status_bar()
        
        # Load tracks
        self._load_tracks()
        
        # Load playlists
        self._load_playlists()
        
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
        
        waveform_settings_action = QAction("Waveform Settings...", self)
        waveform_settings_action.triggered.connect(self._show_waveform_settings)
        view_menu.addAction(waveform_settings_action)
        
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
            self.main_splitter.setSizes([200, 800]) # Restore
        else:
            self.main_splitter.setSizes([0, 1000]) # Collapse
    
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
        self.deck_a.track_dropped.connect(lambda t_id: self._load_track(t_id, "A"))
        decks_layout.addWidget(self.deck_a)
        
        # Deck B
        self.deck_b = DeckWidget("B")
        self.deck_b.track_dropped.connect(lambda t_id: self._load_track(t_id, "B"))
        decks_layout.addWidget(self.deck_b)
        
        main_layout.addWidget(decks_container, 1) # Stretch factor 1
        
        # --- Library Area (Splitter) ---
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar (Left)
        self.sidebar = Sidebar()
        self.sidebar.playlist_created.connect(self._on_playlist_created)
        self.sidebar.item_selected.connect(self._on_sidebar_item_selected)
        self.sidebar.tracks_dropped.connect(self._add_tracks_to_playlist)
        self.main_splitter.addWidget(self.sidebar)
        
        # Track Table (Right)
        self.table_view = LibraryTableView()
        self.table_view.load_to_deck_requested.connect(self._load_track)
        self.table_model = TrackTableModel()
        self.table_view.setModel(self.table_model)
        
        # Set custom delegates
        self.table_view.set_delegates(
            key_column=TrackTableModel.COL_KEY,
            rating_column=TrackTableModel.COL_RATING
        )
        
        # Connect signals
        self.table_view.track_double_clicked.connect(self._on_table_double_clicked)
        self.table_view.analyze_requested.connect(self._on_analyze_requested)
        self.table_view.export_requested.connect(self._on_export_requested)
        self.table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        # Override playlist menu population
        self.table_view._populate_playlist_menu = self._populate_playlist_menu
        
        self.main_splitter.addWidget(self.table_view)
        
        # Set splitter sizes
        self.main_splitter.setSizes([200, 800])
        self.main_splitter.setStretchFactor(1, 1)
        
        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter, 3) # Stretch factor 3 (larger than decks)


    def _on_sidebar_item_selected(self, item_type, item):
        """Handle sidebar navigation"""
        if item_type == "playlist":
            # Load playlist tracks
            playlist_id = item.data(0, Qt.UserRole + 1)
            if playlist_id:
                logger.info(f"Loading tracks from playlist {playlist_id}")
                self._filter_by_playlist(playlist_id)
            else:
                logger.warning("Playlist has no ID")
        elif item_type == "root_playlists":
            # Clear table when clicking on Playlists root
            self.table_model.set_tracks([])
            self.status_bar.showMessage("Select a playlist to view tracks")
        elif item_type == "root_devices":
            # Select root devices
            self.table_model.set_tracks([])
            self.status_bar.showMessage("Select a specific device to view tracks")
        elif item_type == "device":
            # Load tracks from device
            mount_point = item.data(0, Qt.UserRole + 1)
            self._load_device_tracks(mount_point)

    def _load_device_tracks(self, mount_point: str):
        """Load tracks from a device directory"""
        if not mount_point:
            return
        
        from pathlib import Path
        import os
        from src.database.models import Track
        
        self.status_bar.showMessage(f"Scanning device: {mount_point}...")
        self.table_model.set_tracks([])
        
        # extensions to look for
        valid_exts = {'.wav', '.mp3', '.aiff', '.aif', '.flac', '.m4a', '.aac'}
        found_tracks = []
        
        try:
            # Walk directory
            for root, dirs, files in os.walk(mount_point):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in valid_exts:
                        full_path = str(Path(root) / file)
                        
                        # Create temporary track object
                        track = Track(
                            title=file,  # Use filename as title initially
                            file_path=full_path,
                            artist="External",
                            album=self._get_parent_folder_name(root)
                        )
                        # Set a temporary ID to differentiate (not used for DB)
                        track.id = None 
                        found_tracks.append(track)
            
            self.table_model.set_tracks(found_tracks)
            self.status_bar.showMessage(f"Found {len(found_tracks)} tracks on device")
            logger.info(f"Loaded {len(found_tracks)} tracks from device {mount_point}")
            
        except Exception as e:
            logger.error(f"Error scanning device: {e}")
            self.status_bar.showMessage(f"Error scanning device: {str(e)}")

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
            self.status_bar.showMessage(f"Showing {len(tracks)} tracks from playlist")
            logger.info(f"Loaded {len(tracks)} tracks from playlist {playlist_id}")
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
            action.triggered.connect(lambda checked=False, p=playlist, t=track_ids: self._add_tracks_to_playlist(p.id, t))
    
    def _add_tracks_to_playlist(self, playlist_id: int, track_ids: list):
        """Add tracks to a playlist"""
        from src.database.repository import PlaylistRepository
        
        added_count = 0
        for track_id in track_ids:
            if PlaylistRepository.add_track(playlist_id, track_id):
                added_count += 1
        
        if added_count > 0:
            logger.info(f"Added {added_count} tracks to playlist {playlist_id}")
            self.status_bar.showMessage(f"Added {added_count} track(s) to playlist")
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
            QMessageBox.critical(self, "Error", f"Failed to load tracks:\n{str(e)}")
    
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
                QMessageBox.information(self, "No Files", "No audio files found in folder")
    
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
                track_data = {k: v for k, v in track_data.items() if k in valid_keys}
                
                # Create track
                track = self.repository.create(track_data)
                if track:
                    self.table_model.add_track(track)
                    imported_count += 1
                    
            except Exception as e:
                logger.error(f"Error importing {file_path}: {e}")
        
        self.track_count_label.setText(f"{self.table_model.rowCount()} tracks")
        self.status_bar.showMessage(f"Imported {imported_count} new tracks")
        
    def _start_analysis(self, file_paths: list):
        """Start analysis worker"""
        if self.analysis_worker and self.analysis_worker.isRunning():
            QMessageBox.warning(self, "Analysis Running", "Please wait for current analysis to finish")
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
            
            if existing_track:
                # Update existing track
                updated_track = self.repository.update(existing_track.id, analysis_data)
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
                track_data = {k: v for k, v in track_data.items() if k in valid_keys}
                
                track = self.repository.create(track_data)
                if track:
                    self.table_model.add_track(track)
            
            self.track_count_label.setText(f"{self.table_model.rowCount()} tracks")
            
        except Exception as e:
            logger.error(f"Error saving track {file_path}: {e}")
    
    def _on_analysis_finished(self):
        """Analysis finished"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Analysis complete", 3000)
        QMessageBox.information(self, "Analysis Complete", "All tracks have been analyzed")
    
    def _on_analysis_error(self, error: str):
        """Analysis error"""
        logger.error(f"Analysis error: {error}")
        self.status_bar.showMessage(f"Error: {error}", 5000)
    
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
        """Handle selection change - load waveform for selected track"""
        indexes = selected.indexes()
        if not indexes:
            return
        
        # Get first selected row
        row = indexes[0].row()
        track = self.table_model.get_track(row)
        
        if track:
            # For now, just load to A
            self._load_to_deck(self.deck_a)

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
            self.status_bar.showMessage(f"Loaded {track.title} to Deck {deck_widget.deck_id}")

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
        logger.info(f"Analysis requested for {len(track_ids)} tracks: {track_ids}")
        
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
                    QMessageBox.critical(self, "Export Failed", "Failed to export tracks")
            except Exception as e:
                logger.error(f"Export error: {e}")
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
    
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
    
    def _show_waveform_settings(self):
        """Show waveform preferences dialog"""
        from src.ui.dialogs.waveform_preferences import WaveformPreferencesDialog
        from PySide6.QtCore import QSettings
        
        dialog = WaveformPreferencesDialog(self)
        
        # Load saved preferences
        settings = QSettings("ToneMix", "ToneMixPro")
        prefs = {
            'color_scheme': settings.value("waveform/color_scheme", 0, type=int),
            'show_artwork': settings.value("waveform/show_artwork", True, type=bool),
            'show_key': settings.value("waveform/show_key", True, type=bool),
            'show_bpm': settings.value("waveform/show_bpm", True, type=bool),
            'show_beat_grid': settings.value("waveform/show_beat_grid", False, type=bool),
            'intensity': settings.value("waveform/intensity", 1.0, type=float)
        }
        dialog.set_preferences(prefs)
        
        # Connect to apply changes
        dialog.preferences_changed.connect(self._apply_waveform_preferences)
        
        dialog.exec_()
    
    def _apply_waveform_preferences(self, prefs):
        """Apply waveform preferences"""
        from PySide6.QtCore import QSettings
        
        # Save preferences
        settings = QSettings("ToneMix", "ToneMixPro")
        settings.setValue("waveform/color_scheme", prefs['color_scheme'])
        settings.setValue("waveform/show_artwork", prefs['show_artwork'])
        settings.setValue("waveform/show_key", prefs['show_key'])
        settings.setValue("waveform/show_bpm", prefs['show_bpm'])
        settings.setValue("waveform/show_beat_grid", prefs['show_beat_grid'])
        settings.setValue("waveform/intensity", prefs['intensity'])
        
        # Apply to waveform widgets
        if hasattr(self, 'deck_a'):
            self.deck_a.waveform.set_preferences(prefs)
        if hasattr(self, 'deck_b'):
            self.deck_b.waveform.set_preferences(prefs)
        
        logger.info(f"Waveform preferences applied: {prefs}")
    
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
            settings.setValue(f"columns/hidden_{col}", header.isSectionHidden(col))
        
        logger.info("Settings saved")
    
    def closeEvent(self, event):
        """Handle window close - save settings"""
        self._save_settings()
        event.accept()

