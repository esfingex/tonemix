"""
Drop zone widget for file/folder import
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DropZone(QWidget):
    """Drag and drop zone for importing audio files"""
    
    # Signals
    files_dropped = Signal(list)  # List of file paths
    
    # Supported formats
    SUPPORTED_FORMATS = {'.flac', '.aiff', '.wav', '.mp3', '.m4a', '.aif'}
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        
        # Setup UI
        layout = QVBoxLayout(self)
        
        self.label = QLabel("🎵 Drag & Drop Audio Files or Folders Here")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: #b0b0b0;
                font-size: 16px;
                padding: 20px;
            }
        """)
        
        layout.addWidget(self.label)
        
        # Style
        self.setObjectName("DropZone")
        self.setStyleSheet("""
            #DropZone {
                background-color: #252525;
                border: 2px dashed #3a3a3a;
                border-radius: 8px;
            }
            #DropZone:hover {
                border-color: #00d9ff;
                background-color: #2a2a2a;
            }
        """)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.label.setText("📂 Drop files here...")
            self.setStyleSheet("""
                #DropZone {
                    background-color: #2a2a2a;
                    border: 2px solid #00d9ff;
                    border-radius: 8px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self.label.setText("🎵 Drag & Drop Audio Files or Folders Here")
        self.setStyleSheet("""
            #DropZone {
                background-color: #252525;
                border: 2px dashed #3a3a3a;
                border-radius: 8px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop"""
        urls = event.mimeData().urls()
        file_paths = []
        
        for url in urls:
            path = Path(url.toLocalFile())
            
            if path.is_file():
                # Check if supported format
                if path.suffix.lower() in self.SUPPORTED_FORMATS:
                    file_paths.append(str(path))
            elif path.is_dir():
                # Recursively scan directory
                for ext in self.SUPPORTED_FORMATS:
                    file_paths.extend([str(p) for p in path.rglob(f'*{ext}')])
        
        # Reset style
        self.dragLeaveEvent(None)
        
        # Emit signal
        if file_paths:
            logger.info(f"Dropped {len(file_paths)} audio files")
            self.files_dropped.emit(file_paths)
            self.label.setText(f"✅ {len(file_paths)} files ready to import")
        else:
            self.label.setText("⚠️ No supported audio files found")
