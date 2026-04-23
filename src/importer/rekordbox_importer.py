import xml.etree.ElementTree as ET
from pathlib import Path
import urllib.parse
import logging
from typing import Optional

from src.database.repository import TrackRepository, PlaylistRepository

logger = logging.getLogger(__name__)


class RekordboxImporter:
    """Import tracks and playlists from Rekordbox XML"""

    def __init__(self):
        self.tracks_map = {}  # XML TrackID -> Track Object
        self.xml_root_path = None  # Path to the XML file itself

    def parse_xml(self, xml_path: str) -> bool:
        """
        Parse XML and import contents

        Args:
            xml_path: Path to rekordbox.xml file

        Returns:
            Tuple[int, int]: (imported_tracks_count, imported_playlists_count)
        """
        try:
            self.xml_root_path = Path(xml_path).parent
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 1. Import Tracks
            collection = root.find('COLLECTION')
            if collection is not None:
                self._import_collection(collection)

            # 2. Import Playlists
            playlists_node = root.find('PLAYLISTS')
            playlists_count = 0
            if playlists_node is not None:
                playlists_count = self._import_playlists_recursive(
                    playlists_node, "")

            return len(self.tracks_map), playlists_count

        except Exception as e:
            logger.error(f"Error importing Rekordbox XML: {e}")
            raise e

    def _import_collection(self, collection_node: ET.Element):
        """Import tracks from COLLECTION node"""
        for track_node in collection_node.findall('TRACK'):
            try:
                self._import_track(track_node)
            except Exception as e:
                logger.warning(f"Failed to import track: {e}")

    def _resolve_path(self, file_path_str: str) -> Optional[Path]:
        """Resolve file path, handling absolute windows paths on usb mounts"""
        # 1. Direct check
        path_obj = Path(file_path_str)
        if path_obj.exists():
            return path_obj

        # 2. Check relative to XML file
        if not self.xml_root_path:
            return None

        # Strategy: Try to match common parent folders.
        parts = list(path_obj.parts)

        # Limit to depth of 5 to avoid trying too many combinations
        max_depth = 5

        for i in range(1, min(len(parts), max_depth) + 1):
            partial = Path(*parts[-i:])  # Last i parts
            candidate = self.xml_root_path / partial
            if candidate.exists():
                return candidate

        return None

    def _import_track(self, track_node: ET.Element):
        """Import single track"""
        track_id = track_node.get('TrackID')
        location = track_node.get('Location')

        if not location or not track_id:
            return

        # Parse URL (file://localhost/...)
        parsed_url = urllib.parse.urlparse(location)
        file_path = urllib.parse.unquote(parsed_url.path)

        # Windows path fix
        if file_path.startswith('/') and ':' in file_path[2:4]:
            file_path = file_path[1:]

        # Resolve Path
        path_obj = self._resolve_path(file_path)

        if not path_obj:
            logger.warning(f"File not found (fuzzy match failed): {file_path}")
            return

        # Check if already in DB
        existing_track = TrackRepository.get_by_path(str(path_obj))

        # Parse Metadata from XML
        bpm = float(track_node.get('AverageBpm', 0))
        key = track_node.get('Tonality')

        # Map Rating 0-255 -> 0-5
        # RB uses 0-255. 255=5 stars, 51 per star (approx)
        rating_raw = int(track_node.get('Rating', 0) or 0)
        rating = rating_raw // 51 if track_node.get('Rating') else 0

        track_data = {
            'title': track_node.get('Name'),
            'artist': track_node.get('Artist'),
            'album': track_node.get('Album'),
            'genre': track_node.get('Genre'),
            'bpm': bpm,
            'key_camelot': key,
            'rating': rating,
            'duration_seconds': int(track_node.get('TotalTime', 0)),
        }

        if existing_track:
            # Update missing metadata
            updates = {}
            if bpm and (not existing_track.bpm or existing_track.bpm == 0):
                updates['bpm'] = bpm
            if key and not existing_track.key_camelot:
                updates['key_camelot'] = key
            if rating and existing_track.rating == 0:
                updates['rating'] = rating

            if updates:
                TrackRepository.update(existing_track.id, updates)

            self.tracks_map[track_id] = existing_track
        else:
            # Create new track
            track_data['file_path'] = str(path_obj)
            track = TrackRepository.create(track_data)
            if track:
                self.tracks_map[track_id] = track

    def _import_playlists_recursive(self, node: ET.Element,
                                    path_prefix: str = "") -> int:
        """
        Import playlists recursively, flattening hierarchy into name.
        Example: Folder / Subfolder / Playlist
        """
        count = 0

        # NODE Type 0: Folder, 1: Playlist
        for child_node in node.findall('NODE'):
            node_type = child_node.get('Type')
            name = child_node.get('Name')

            if not name:
                continue

            if name == "ROOT":
                new_prefix = ""
            else:
                new_prefix = f"{path_prefix} / {name}" if path_prefix else name

            if node_type == '0':  # Folder
                count += self._import_playlists_recursive(child_node,
                                                          new_prefix)

            elif node_type == '1':  # Playlist
                playlist_name = new_prefix
                playlist = PlaylistRepository.create(playlist_name)
                if playlist:
                    count += 1
                    # Add tracks
                    for track_key in child_node.findall('TRACK'):
                        rb_track_id = track_key.get('Key')
                        if rb_track_id in self.tracks_map:
                            track = self.tracks_map[rb_track_id]
                            PlaylistRepository.add_track(playlist.id, track.id)

        return count
