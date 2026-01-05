"""
Main application window
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QSplitter, QStatusBar, QProgressBar, QLabel,
                                QPushButton, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction
from pathlib import Path
import logging

from src.ui.widgets.waveform_widget import WaveformWidget
from src.ui.widgets.library_table_view import LibraryTableView
from src.ui.widgets.drop_zone import DropZone
from src.ui.models import TrackTableModel
from src.database.repository import TrackRepository
from src.core.analyzer import AudioAnalyzer
from src.core.audio_processor import AudioProcessor
from src.export.rekordbox_exporter import RekordboxExporter

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Worker thread for audio analysis"""
    
    progress = Signal(int, int)  # current, total
    track_analyzed = Signal(str, object)  # file_path, TrackAnalysis
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, file_paths: list):
        super().__init__()
        self.file_paths = file_paths
        self.analyzer = AudioAnalyzer()
    
    def run(self):
        """Run analysis"""
        try:
            total = len(self.file_paths)
            
            for i, file_path in enumerate(self.file_paths):
                try:
                    result = self.analyzer.analyze_track(file_path)
                    if result:
                        self.track_analyzed.emit(file_path, result)
                    self.progress.emit(i + 1, total)
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
        self._create_ui()
        self._create_status_bar()
        
        # Load tracks
        self._load_tracks()
        
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
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_ui(self):
        """Create main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)
        
        # Splitter for waveform and table
        splitter = QSplitter(Qt.Vertical)
        
        # Waveform widget
        self.waveform = WaveformWidget()
        splitter.addWidget(self.waveform)
        
        # Table view
        self.table_model = TrackTableModel()
        self.table_view = LibraryTableView()
        self.table_view.setModel(self.table_model)
        
        # Set custom delegates
        self.table_view.set_delegates(
            key_column=TrackTableModel.COL_KEY,
            rating_column=TrackTableModel.COL_RATING
        )
        
        # Connect signals
        self.table_view.track_double_clicked.connect(self._on_track_double_clicked)
        self.table_view.analyze_requested.connect(self._on_analyze_requested)
        self.table_view.export_requested.connect(self._on_export_requested)
        
        splitter.addWidget(self.table_view)
        
        # Set splitter sizes
        splitter.setSizes([200, 500])
        
        layout.addWidget(splitter)
    
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
        self._start_analysis(file_paths)
    
    def _import_files(self):
        """Import files dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Audio Files",
            "",
            "Audio Files (*.flac *.aiff *.wav *.mp3 *.m4a)"
        )
        
        if files:
            self._start_analysis(files)
    
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
                self._start_analysis(files)
            else:
                QMessageBox.information(self, "No Files", "No audio files found in folder")
    
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
        try:
            # Get audio info
            audio_info = self.audio_processor.get_audio_info(file_path)
            
            # Create track data
            track_data = {
                'title': Path(file_path).stem,
                'file_path': file_path,
                'key_camelot': analysis.key_camelot,
                'key_musical': analysis.key_musical,
                'bpm': analysis.bpm,
                'energy_level': analysis.energy_level,
                'duration_seconds': analysis.duration_seconds,
                'waveform_data': self.audio_processor.waveform_to_bytes(analysis.waveform_data),
                **audio_info
            }
            
            # Save to database
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
        track = self.repository.get_by_id(track_id)
        if track and track.waveform_data:
            waveform = self.audio_processor.bytes_to_waveform(track.waveform_data)
            self.waveform.set_waveform(waveform, track.duration_seconds)
            self.status_bar.showMessage(f"Loaded: {track.title} - {track.artist}")
    
    def _on_analyze_requested(self, track_ids: list):
        """Re-analyze tracks"""
        # Get file paths
        file_paths = []
        for track_id in track_ids:
            track = self.repository.get_by_id(track_id)
            if track:
                file_paths.append(track.file_path)
        
        if file_paths:
            self._start_analysis(file_paths)
    
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
