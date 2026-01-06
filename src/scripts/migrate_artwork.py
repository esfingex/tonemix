"""
Migration script to add artwork_thumbnail column and populate it
"""
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

from src.database.connection import get_session
from src.database.models import Track
from src.core.audio_processor import AudioProcessor
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

def migrate():
    print("Starting migration...")
    
    # 1. Add column if not exists
    with get_session() as session:
        try:
            session.execute(text("ALTER TABLE tracks ADD COLUMN artwork_thumbnail BLOB"))
            print("Added artwork_thumbnail column")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column already exists")
            else:
                print(f"Error adding column: {e}")
                return

    # 2. Extract artwork for existing tracks
    processor = AudioProcessor()
    
    with get_session() as session:
        tracks = session.query(Track).all()
        print(f"Found {len(tracks)} tracks to process")
        
        count = 0
        for track in tracks:
            if track.file_path and not track.artwork_thumbnail:
                try:
                    artwork = processor.extract_artwork(track.file_path)
                    if artwork:
                        track.artwork_thumbnail = artwork
                        count += 1
                        if count % 10 == 0:
                            print(f"Processed {count} tracks...")
                except Exception as e:
                    print(f"Error processing {track.title}: {e}")
        
        session.commit()
        print(f"Migration complete. Updated {count} tracks with artwork.")

if __name__ == "__main__":
    migrate()
