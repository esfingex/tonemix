"""
Rekordbox XML exporter
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List
from datetime import datetime
import logging
from pathlib import Path

from src.database.models import Track
from src.utils.config import config

logger = logging.getLogger(__name__)


class RekordboxExporter:
    """Export track library to Rekordbox XML format"""
    
    def __init__(self):
        self.version = config.export.get('rekordbox_xml_version', '1.0.0')
    
    def export_library(self, tracks: List[Track], output_path: str) -> bool:
        """
        Export tracks to Rekordbox XML
        
        Args:
            tracks: List of Track objects
            output_path: Output XML file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Exporting {len(tracks)} tracks to Rekordbox XML")
            
            # Create root element
            root = ET.Element('DJ_PLAYLISTS', Version=self.version)
            
            # Add product info
            product = ET.SubElement(root, 'PRODUCT', Name='ToneMix Pro', Version='0.1.0', Company='ToneMix')
            
            # Create collection
            collection = ET.SubElement(root, 'COLLECTION', Entries=str(len(tracks)))
            
            # Add tracks
            for track in tracks:
                self._add_track_node(collection, track)
            
            # Create playlists node (empty for now)
            playlists = ET.SubElement(root, 'PLAYLISTS')
            
            # Convert to pretty XML
            xml_str = self._prettify_xml(root)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            logger.info(f"Rekordbox XML exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting Rekordbox XML: {e}")
            return False
    
    def _add_track_node(self, parent: ET.Element, track: Track):
        """Add track node to XML"""
        
        # Determine file location (use transcoded path if available)
        file_location = track.transcoded_path if track.is_transcoded else track.file_path
        
        # Convert to file:// URL
        file_url = f"file://localhost{Path(file_location).as_posix()}"
        
        # Create track element
        track_elem = ET.SubElement(parent, 'TRACK', 
            TrackID=str(track.id),
            Name=track.title or '',
            Artist=track.artist or '',
            Album=track.album or '',
            Genre=track.genre or '',
            Kind=track.file_format or '',
            Size=str(track.file_size_bytes or 0),
            TotalTime=str(int(track.duration_seconds or 0)),
            BitRate=str(track.bitrate or 0),
            SampleRate=str(track.sample_rate or 44100),
            Tonality=track.key_camelot or '',
            AverageBpm=f"{track.bpm:.2f}" if track.bpm else '0.00',
            Rating=str(track.rating or 0),
            Location=file_url
        )
        
        # Add optional fields
        if track.year:
            track_elem.set('Year', str(track.year))
        
        if track.comment:
            track_elem.set('Comments', track.comment)
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
