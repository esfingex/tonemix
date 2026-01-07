import sys
import os
sys.path.append(os.getcwd())
from src.export.rekordbox_exporter import RekordboxExporter
from src.database.models import Track
import logging

# Configure logging to see output
logging.basicConfig(level=logging.INFO)

# Mock Track
# Note: we need to satisfy basic Track attributes used by exporter
t1 = Track(id=1, title="Test Track 1", artist="Artist A", 
           bpm=120.0, key_camelot="8A", duration_seconds=180,
           file_path="/home/esfingex/Music/track1.mp3",
           file_format="mp3")

t2 = Track(id=2, title="Test Track 2", artist="Artist B", 
           bpm=124.0, key_camelot="9A", duration_seconds=200,
           file_path="/home/esfingex/Music/track2.wav",
           file_format="wav")

exporter = RekordboxExporter()
output = "test_rekordbox.xml"

print("Exporting playlist...")
success = exporter.export_playlist([t1, t2], "USB Export Test", output)

if success:
    print(f"Export Success! File created: {output}")
    if os.path.exists(output):
        print("--- XML CONTENT ---")
        with open(output, 'r') as f:
            print(f.read())
        print("--- END XML ---")
        os.remove(output)
else:
    print("Export Failed")
