"""
ToneMix Pro - Professional Music Analysis Software
Main application entry point
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from src.utils.config import config


def main():
    """Main application entry point"""
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ToneMix Pro")
    app.setOrganizationName("ToneMix")
    app.setApplicationVersion("0.1.0")
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # TODO: Initialize database
    # from src.database.connection import init_database
    # init_database()
    
    # TODO: Load stylesheet
    # stylesheet_path = Path(__file__).parent / "src" / "ui" / "resources" / "styles.qss"
    # if stylesheet_path.exists():
    #     with open(stylesheet_path, 'r') as f:
    #         app.setStyleSheet(f.read())
    
    # TODO: Create and show main window
    # from src.ui.main_window import MainWindow
    # window = MainWindow()
    # window.show()
    
    print("🎵 ToneMix Pro v0.1.0")
    print("=" * 50)
    print("Configuration loaded successfully!")
    print(f"Database: {config.database.get('host')}:{config.database.get('port')}")
    print(f"Audio sample rate: {config.audio.get('sample_rate')} Hz")
    print(f"Waveform points: {config.audio.get('waveform_points')}")
    print("=" * 50)
    print("\n⚠️  UI components not yet implemented")
    print("Next steps:")
    print("  1. Implement database models")
    print("  2. Create audio analysis engine")
    print("  3. Build UI components")
    print("\nPress Ctrl+C to exit...")
    
    # For now, just keep the app running
    # return app.exec()
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
