"""
ToneMix Pro - Professional Music Analysis Software
Main application entry point
"""
import sys
import os
import logging
from pathlib import Path

# Force Qt to use X11 instead of Wayland (NVIDIA OpenGL compatibility)
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_XCB_GL_INTEGRATION'] = 'xcb_glx'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.utils.config import config
from src.database.connection import init_database
from src.ui.main_window import MainWindow

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
    
    # High DPI scaling is enabled by default in Qt 6
    # app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    try:
        # Display configuration
        print("\n📋 Configuration:")
        print(f"  Database: {config.database.get('host')}:{config.database.get('port')}/{config.database.get('name')}")
        print(f"  Audio sample rate: {config.audio.get('sample_rate')} Hz")
        print(f"  Waveform points: {config.audio.get('waveform_points')}")
        print(f"  Key profile: {config.analysis.get('key_profile')}")
        
        # Initialize database
        print("\n🗄️  Initializing database...")
        db_type = config.database.get('type', 'postgresql')
        print(f"  Using database engine: {db_type.upper()}")
        
        if init_database():
            print("  ✅ Database initialized successfully")
        else:
            print("  ⚠️  Database initialization failed")
            if db_type == 'postgresql':
                print("  Make sure PostgreSQL is running and credentials are correct in .env")
            QMessageBox.critical(
                None,
                "Database Error",
                "Failed to initialize database."
            )
            return 1
        
        # Check components
        print("\n🔧 Checking components:")
        
        # Check Essentia
        try:
            import essentia
            print("  ✅ Essentia available")
        except ImportError:
            print("  ⚠️  Essentia not installed (pip install essentia)")
            print("     Key and BPM detection will use fallback methods")
        
        # Check FFmpeg
        import shutil
        if shutil.which('ffmpeg'):
            print("  ✅ FFmpeg available")
        else:
            print("  ⚠️  FFmpeg not found (sudo apt install ffmpeg)")
            print("     Transcoding will not be available")
        
        print("\n" + "=" * 60)
        print("✅ ToneMix Pro is ready!")
        print("=" * 60)
        
        # Load stylesheet
        stylesheet_path = Path(__file__).parent / "src" / "ui" / "resources" / "styles.qss"
        if stylesheet_path.exists():
            with open(stylesheet_path, 'r') as f:
                app.setStyleSheet(f.read())
            print("\n🎨 Dark theme loaded")
        
        # Create and show main window
        print("🚀 Launching UI...\n")
        window = MainWindow()
        window.show()
        
        return app.exec()
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        QMessageBox.critical(None, "Error", f"Application failed to start:\n{str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


