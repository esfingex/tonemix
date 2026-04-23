import sys
import os
import urllib.parse
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.importer.pdb_importer import DeviceSqlImporter
from src.exporters.rekordbox_xml_exporter import RekordboxXmlExporter

def generate_xml():
    db_path = "/media/esfingex/IVIR_R1/PIONEER/Rekordbox/export.pdb"
    output_path = "/media/esfingex/IVIR_R1/rekordbox.xml"
    
    if not os.path.exists(db_path):
        print(f"Error: PDB not found at {db_path}")
        return

    print(f"Reading PDB from {db_path}...")
    importer = DeviceSqlImporter()
    if not importer.open(db_path):
        print("Failed to open PDB")
        return

    # 1. Read Playlists
    # This naturally reads tracks if we iterate them
    raw_playlists = importer.read_playlists()
    print(f"Found {len(raw_playlists)} playlists.")

    # 2. Collect All Tracks and Map to Playlists
    all_tracks = {} # Map ID -> TrackDict
    xml_playlists = []

    for p in raw_playlists:
        p_id = p['id']
        p_name = p['name']
        print(f"  - Processing '{p_name}' (ID: {p_id})...")
        
        # Get tracks for this playlist
        # This uses the fixed logic (Offset Scavenger + Contiguous Fallback)
        tracks = importer.get_playlist_tracks(p_id)
        
        # Store track IDs for this playlist
        p_track_ids = []
        for t in tracks:
            t_id = t['id']
            p_track_ids.append(t_id)
            
            # Add to global collection if new
            if t_id not in all_tracks:
                all_tracks[t_id] = t
        
        xml_playlists.append({
            'name': p_name,
            'id': p_id,
            'track_ids': p_track_ids
        })

    importer.close()
    
    # 3. Export to XML
    print(f"\nCollected {len(all_tracks)} unique tracks.")
    print("Generating XML...")
    
    exporter = RekordboxXmlExporter()
    
    # Convert dict to list
    track_list = list(all_tracks.values())
    exporter.add_tracks(track_list)
    exporter.add_playlists(xml_playlists)
    
    exporter.export(output_path)
    print("Done!")

if __name__ == "__main__":
    generate_xml()
