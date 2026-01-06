from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox

class DeletePlaylistDialog(QDialog):
    """Custom dialog for playlist deletion"""
    def __init__(self, playlist_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete Playlist")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        
        # Message
        layout.addWidget(QLabel(f"Are you sure you want to delete playlist '{playlist_name}'?"))
        
        # Warning for file deletion
        self.chk_delete_files = QCheckBox("\u26a0\ufe0f Also delete audio files from DISK (Permanent)")
        self.chk_delete_files.setStyleSheet("color: #ff5555; font-weight: bold;")
        self.chk_delete_files.setToolTip("Checking this will PERMANENTLY delete the audio files from your computer.\nThis cannot be undone.")
        layout.addWidget(self.chk_delete_files)
        
        layout.addSpacing(10)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def should_delete_files(self):
        return self.chk_delete_files.isChecked()
