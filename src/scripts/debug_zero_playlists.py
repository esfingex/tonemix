import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.importer.pdb_importer import DeviceSqlImporter

# Quick debug: check if read_playlists is returning anything
path = "/media/esfingex/IVIR_R1/PIONEER/Rekordbox/export.pdb"
importer = DeviceSqlImporter()

if importer.open(path):
    # Call the internal method to see raw results before cleaning
    print("Testing playlist reading...")
    playlists = importer.read_playlists()
    print(f"Result: {len(playlists)} playlists")
    if len(playlists) == 0:
        print("ERROR: No playlists returned!")
    else:
        for p in playlists[:5]:
            print(f"  - {p}")
    importer.close()
else:
    print("Failed to open PDB")
