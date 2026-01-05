"""
ToneMix Pro - Professional Music Analysis Software
Main application entry point
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.utils.config import config
from src.database.connection import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    
    print("=" * 60)
    print("🎵 ToneMix Pro v0.1.0")
    print("Professional Music Analysis Software")
    print("=" * 60)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ToneMix Pro")
    app.setOrganizationName("ToneMix")
    app.setApplicationVersion("0.1.0")
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    try:
        # Display configuration
        print("\n📋 Configuration:")
        print(f"  Database: {config.database.get('host')}:{config.database.get('port')}/{config.database.get('name')}")
        print(f"  Audio sample rate: {config.audio.get('sample_rate')} Hz")
        print(f"  Waveform points: {config.audio.get('waveform_points')}")
        print(f"  Key profile: {config.analysis.get('key_profile')}")
        
        # Initialize database
        print("\n🗄️  Initializing database...")
        if init_database():
            print("  ✅ Database initialized successfully")
        else:
            print("  ⚠️  Database initialization failed")
            print("  Make sure PostgreSQL is running and credentials are correct in .env")
            return 1
        
        # Check components
        print("\n🔧 Checking components:")
        
        # Check Essentia
        try:
            import essentia
            print("  ✅ Essentia available")
        except ImportError:
            print("  ⚠️  Essentia not installed (pip install essentia)")
        
        # Check FFmpeg
        import shutil
        if shutil.which('ffmpeg'):
            print("  ✅ FFmpeg available")
        else:
            print("  ⚠️  FFmpeg not found (sudo apt install ffmpeg)")
        
        print("\n" + "=" * 60)
        print("✅ ToneMix Pro is ready!")
        print("=" * 60)
        
        # TODO: Load and show main window
        # from src.ui.main_window import MainWindow
        # window = MainWindow()
        # window.show()
        # return app.exec()
        
        print("\n⚠️  UI not yet implemented")
        print("\n📦 Available modules:")
        print("  ✅ Database layer (models, connection, repository)")
        print("  ✅ Audio analyzer (key, BPM, energy detection)")
        print("  ✅ Audio processor (loading, waveform generation)")
        print("  ✅ Transcoder (FLAC to AIFF)")
        print("  ✅ Rekordbox exporter (XML generation)")
        print("  ⏳ UI components (coming soon)")
        
        print("\n🚀 Next steps:")
        print("  1. Implement main window UI")
        print("  2. Create waveform widget")
        print("  3. Build library table view")
        print("  4. Add file import functionality")
        
        print("\n👋 Press Enter to exit...")
        input()
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        QMessageBox.critical(None, "Error", f"Application failed to start:\n{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

