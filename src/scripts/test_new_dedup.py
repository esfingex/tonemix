import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.importer.pdb_importer import DeviceSqlImporter

def list_all():
    path = "/media/esfingex/IVIR_R1/PIONEER/Rekordbox/export.pdb"
    importer = DeviceSqlImporter()
    
    if not importer.open(path):
        print("Failed to open PDB")
        return
    
    playlists = importer.read_playlists()
    
    print(f"\n=== Found {len(playlists)} playlists ===\n")
    for i, p in enumerate(playlists, 1):
        print(f"{i:2d}. {p['name']:<30} (ID: {p['id']}, Tracks: {p['count']})")
    
    importer.close()

if __name__ == "__main__":
    list_all()
