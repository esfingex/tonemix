import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Optional
import urllib.parse
import os

class RekordboxXmlExporter:
    """
    Exports ToneMix library (Tracks and Playlists) to a rekordbox.xml file.
    Follows the standard Rekordbox XML schema.
    """

    def __init__(self):
        self.root = ET.Element("DJ_PLAYLISTS")
        self.root.set("Version", "1.0.0")
        self.collection = ET.SubElement(self.root, "COLLECTION")
        self.playlists = ET.SubElement(self.root, "PLAYLISTS")
        self.track_id_map = {} # Maps ToneMix ID -> XML Track ID (integer)
        self.next_xml_id = 1

    def add_tracks(self, tracks: List[Dict]):
        """
        Adds tracks to the COLLECTION section.
        Expected track dict structure:
        {
            'id': int, 'title': str, 'artist': str, 'path': str, 
            'bpm': float, 'genre': str, 'key': str, ...
        }
        """
        self.collection.set("Entries", str(len(tracks)))
        
        for t in tracks:
            # Generate a new sequential ID for the XML to ensure uniqueness
            xml_id = self.next_xml_id
            self.track_id_map[t['id']] = xml_id
            self.next_xml_id += 1
            
            # Create Track Element
            track = ET.SubElement(self.collection, "TRACK")
            track.set("TrackID", str(xml_id))
            track.set("Name", t.get('title', 'Unknown'))
            track.set("Artist", t.get('artist', 'Unknown'))
            track.set("Kind", self._guess_kind(t.get('path', '')))
            track.set("Size", "0") # TODO: Get file size
            track.set("TotalTime", "0") # TODO: Get duration
            
            # Path handling: Must be URL encoded absolute path
            # e.g. file://localhost/media/esfingex/...
            raw_path = t.get('path', '')
            if not raw_path.startswith('file://'):
                # Ensure it's absolute
                if not raw_path.startswith('/'):
                     # Attempt strict resolution or leave as is?
                     pass 
                
                # Encode
                encoded_path = "file://localhost" + urllib.parse.quote(raw_path)
                track.set("Location", encoded_path)
            else:
                track.set("Location", raw_path)

            if 'bpm' in t:
                track.set("AverageBpm", str(t['bpm']))
            
            # Add other metadata fields as needed

    def add_playlists(self, playlists: List[Dict]):
        """
        Adds playlists to the PLAYLISTS section.
        Expected structure: List of dicts with 'name', 'id' and 'tracks' (list of IDs)
        """
        # Create Root Folder Node
        root_node = ET.SubElement(self.playlists, "NODE")
        root_node.set("Type", "0")
        root_node.set("Name", "ROOT")
        root_node.set("Count", str(len(playlists)))
        
        for p in playlists:
            node = ET.SubElement(root_node, "NODE")
            node.set("Name", p.get('name', 'Unknown'))
            node.set("Type", "1") # 1 = Playlist
            node.set("KeyType", "0")
            
            track_ids = p.get('track_ids', [])
            node.set("Entries", str(len(track_ids)))
            
            for tid in track_ids:
                if tid in self.track_id_map:
                    xml_tid = self.track_id_map[tid]
                    track_node = ET.SubElement(node, "TRACK")
                    track_node.set("Key", str(xml_tid))

    def _guess_kind(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        if ext == '.mp3': return 'MP3 File'
        if ext == '.wav': return 'WAV File'
        if ext == '.aiff' or ext == '.aif': return 'AIFF File'
        if ext == '.flac': return 'FLAC File'
        if ext == '.m4a': return 'M4A File'
        return 'Unknown File'

    def export(self, output_path: str):
        """Writes the XML to file."""
        # Prettify
        string = ET.tostring(self.root, 'utf-8')
        reparsed = minidom.parseString(string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        print(f"Exported XML to {output_path}")
