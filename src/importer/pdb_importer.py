import logging
import struct
import re
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class PDBPage:
    """Represents a 4KB page in the PDB file."""
    SIZE = 4096

    def __init__(self, data: bytes, page_index: int):
        self.data = data
        self.index = page_index

    def get_type(self) -> int:
        """Get page type from offset 12 (4 bytes)"""
        if len(self.data) < 16:
            return 0
        return struct.unpack_from('<I', self.data, 12)[0]

    def get_next_page_index(self) -> int:
        """Get next page index from offset 8 (4 bytes)"""
        if len(self.data) < 12:
            return 0
        next_idx = struct.unpack_from('<I', self.data, 8)[0]
        # Sanity check
        if next_idx == 0xFFFFFFFF or next_idx == 0:
            return 0
        return next_idx


class DeviceSqlImporter:
    """
    Importer for Pioneer DeviceSQL (PDB) binary files.
    Reads playlists and track metadata from Rekordbox USB exports.
    """

    PAGE_SIZE = 4096

    def __init__(self):
        self.file_handle = None
        self.file_path = None
        self.tables = {}  # Cache for table page indices

    def open(self, file_path: str) -> bool:
        """Open a PDB file for reading."""
        try:
            self.file_path = Path(file_path)
            if not self.file_path.exists():
                logger.error(f"PDB file not found: {file_path}")
                return False

            self.file_handle = open(self.file_path, 'rb')
            
            # Read and parse header (Page 0)
            self._read_header()
            
            return True
        except Exception as e:
            logger.error(f"Failed to open PDB: {e}")
            return False

    def close(self):
        """Close the PDB file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None

    def _read_header(self):
        """Read Page 0 (File Header) and build table directory."""
        header_page = self.read_page(0)
        if not header_page:
            return

        # Parse table directory from header
        # Tables are listed with their type and first page index
        self.tables['Playlists'] = self._find_table_by_type(0x2E)  # Type 0x2E (46) = Playlists
        self.tables['Tracks'] = self._find_table_by_type(0x8A)     # Type 138 = Tracks
        self.tables['PlaylistMap'] = self._find_table_by_type(0x36)  # Type 54 = Playlist-Track mapping

    def _find_table_by_type(self, table_type: int) -> int:
        """
        Scan all pages to find the first page of a given table type.
        Returns page index, or 0 if not found.
        """
        try:
            file_size = self.file_path.stat().st_size
            num_pages = file_size // self.PAGE_SIZE

            for page_idx in range(num_pages):
                page_data = self.read_page(page_idx)
                if not page_data:
                    continue

                # Check page type at offset 12
                try:
                    page_type = struct.unpack_from('<I', page_data, 12)[0]
                    if page_type == table_type:
                        return page_idx
                except:
                    continue

            return 0
        except Exception as e:
            logger.error(f"Error finding table type {table_type:02X}: {e}")
            return 0

    def read_page(self, page_index: int) -> Optional[bytes]:
        """Read a 4KB page from the PDB file."""
        try:
            if not self.file_handle:
                return None

            offset = page_index * self.PAGE_SIZE
            self.file_handle.seek(offset)
            data = self.file_handle.read(self.PAGE_SIZE)

            if len(data) != self.PAGE_SIZE:
                return None

            return data
        except Exception as e:
            logger.error(f"Failed to read page {page_index}: {e}")
            return None

    def read_playlists(self) -> List[Dict]:
        """
        Read playlists from the PDB file.
        Returns list of dicts with keys: name, id, count
        """
        
        candidates = {}  # Name -> Set of potential IDs
        id_frequency = {}  # ID -> Count of rows it appeared in
        
        # Scan ALL pages for type 0x2E (Playlists), not just follow chain
        # because the chain includes other table types
        file_size = self.file_path.stat().st_size
        num_pages = file_size // self.PAGE_SIZE
        
        for page_idx in range(num_pages):
            page_data = self.read_page(page_idx)
            if not page_data:
                continue
            
            # Check if this page is type 0x2E (Playlists)
            try:
                page_type = struct.unpack_from('<I', page_data, 12)[0]
                if page_type != 0x2E:
                    continue
            except:
                continue
            
            # This is a Playlist page - extract names
            try:
                # Simplified approach: scan entire page for playlist-like strings
                pattern = re.compile(b'[a-zA-Z][a-zA-Z0-9 _#]{3,40}')
                
                for match in pattern.finditer(page_data):
                    text = match.group().decode('utf-8', errors='ignore').strip()
                    
                    # Skip very short names or common garbage
                    if len(text) < 4 or text in ['ROOT', 'Playlists', 'Tracks']:
                        continue
                    
                    # Extract playlist ID from structure
                    # Structure: [12 bytes][4 bytes: ID][other fields][1 byte: length][string]
                    # So ID is at offset - 13 (1 byte length + 12 bytes before ID)
                    match_offset = match.start()
                    
                    if match_offset >= 13:
                        try:
                            playlist_id = struct.unpack_from('<I', page_data, match_offset - 13)[0]
                            
                            # Sanity check: ID should be reasonable (0-20000)
                            if 0 < playlist_id < 20000:
                                if text not in candidates:
                                    candidates[text] = set()
                                candidates[text].add(playlist_id)
                                id_frequency[playlist_id] = id_frequency.get(playlist_id, 0) + 1
                        except:
                            pass
            
            except Exception:
                pass
        
        # 3. Resolution
        active_counts = self._count_tracks_per_playlist()
        
        results = []
        for name, potential_ids in candidates.items():
            best_id = 0
            max_count = -1
            
            for pid in potential_ids:
                count = active_counts.get(pid, 0)
                freq = id_frequency.get(pid, 1)
                
                if count <= 0:
                    score = -1
                else:
                    if freq == 0: freq = 1
                    score = (10000 / count) / freq
                
                if score > max_count:
                    max_count = score
                    best_id = pid
                elif score == max_count and score > -1:
                    best_id = max(best_id, pid)
                    
            if best_id > 0:
                if name not in ['Playlists', 'ROOT']:
                    final_count = active_counts.get(best_id, 0)
                    results.append({'name': name, 'id': best_id, 'count': final_count})
        
        # 4. Name Cleaning (Regex-based)
        # Remove garbage suffixes and leading symbols to match Rekordbox display
        
        # First pass: Clean each name individually
        for r in results:
            name = r['name']
            # Remove leading # and other symbols
            name = re.sub(r'^[^a-zA-Z0-9]+', '', name)
            
            # Remove trailing garbage patterns:
            # 1. "Vol2 111" → "Vol2" (space + 2+ repeated/multi digits)
            name = re.sub(r'\s+(\d)\1+$', '', name)  # Repeated digits like 111, 222
            name = re.sub(r'\s+\d{2,}$', '', name)   # Multi-digit like 11, 22
            name = re.sub(r'\s+(\d)\s+\1$', '', name)  # Spaced repetition like " 1 1", " 2 2"
            # 2. "Vol13" → "Vol1" (trailing digits after Vol+digit)
            name = re.sub(r'(Vol\s*\d)(\d+)$', r'\1', name, flags=re.IGNORECASE)
            # 3. "Fenix22" → "Fenix2" (trailing digits after word+digit)
            name = re.sub(r'([a-zA-Z]\d)(\d+)$', r'\1', name)
            
            r['name'] = name
        
        # Second pass: Remove duplicates (keep shortest)
        results.sort(key=lambda x: len(x['name']))
        
        clean_results = []
        seen_names = set()
        
        for r in results:
            name_lower = r['name'].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                clean_results.append(r)
        
        # Sort alphabetically for output
        clean_results.sort(key=lambda x: x['name'])
        return clean_results

    def _count_tracks_per_playlist(self) -> Dict[int, int]:
        """Scan PlaylistMap (0x36) to count tracks for each PlaylistID."""
        counts = {}
        if 'PlaylistMap' not in self.tables:
            self.tables['PlaylistMap'] = self._find_table_by_type(0x36)
            
        if 'PlaylistMap' not in self.tables:
            return counts
            
        map_idx = self.tables['PlaylistMap']
        visited = set()
        
        while map_idx != 0xFFFFFFFF and map_idx not in visited:
            visited.add(map_idx)
            page_data = self.read_page(map_idx)
            if not page_data: break
            
            try:
                num_rows = struct.unpack_from('<H', page_data, 26)[0] & 0x1FFF
                for i in range(num_rows):
                    ofs = 4096 - 6 - (2*i)
                    if ofs < 0: break
                    row_offset = struct.unpack_from('<H', page_data, ofs)[0]
                    if 0 < row_offset < 4096 - 8:
                        p_id = struct.unpack_from('<I', page_data, row_offset)[0]
                        counts[p_id] = counts.get(p_id, 0) + 1
            except: pass
            
            next_p = struct.unpack_from('<I', page_data, 12)[0]
            if next_p == map_idx: break
            map_idx = next_p
            if map_idx == 0: break
            
        return counts

    def get_playlist_tracks(self, playlist_id: int) -> List[Dict]:
        """Get all tracks for a given playlist ID."""
        if 'PlaylistMap' not in self.tables:
            self.tables['PlaylistMap'] = self._find_table_by_type(0x36)

        if 'PlaylistMap' not in self.tables:
            return []

        track_ids = []
        map_page_idx = self.tables['PlaylistMap']
        current_idx = map_page_idx
        visited = set()

        while current_idx != 0xFFFFFFFF and current_idx not in visited:
            visited.add(current_idx)
            page_data = self.read_page(current_idx)
            if not page_data:
                break
            
            try:
                num_rows = struct.unpack_from('<H', page_data, 26)[0] & 0x1FFF
                for i in range(num_rows):
                    ofs_pos = 4096 - 6 - (2*i)
                    if ofs_pos < 0: break
                    row_offset = struct.unpack_from('<H', page_data, ofs_pos)[0]
                    
                    if 0 < row_offset < 4096 - 8:
                        p_id = struct.unpack_from('<I', page_data, row_offset)[0]
                        if p_id == playlist_id:
                             t_id = struct.unpack_from('<I', page_data, row_offset + 4)[0]
                             track_ids.append(t_id)

            except Exception:
                pass

            next_p = struct.unpack_from('<I', page_data, 12)[0]
            if next_p == current_idx: break
            current_idx = next_p
            if current_idx == 0: break

        all_tracks = self.get_tracks_by_ids(set(track_ids))

        ordered_tracks = []
        for tid in track_ids:
            if tid in all_tracks:
                ordered_tracks.append(all_tracks[tid])

        return ordered_tracks

    def get_tracks_by_ids(self, target_ids: set) -> Dict[int, Dict]:
        """Fetch track metadata for given track IDs."""
        results = {}
        if 'Tracks' not in self.tables:
            self.tables['Tracks'] = self._find_table_by_type(0x8A)
            
        if 'Tracks' not in self.tables:
            return results

        current_idx = self.tables['Tracks']
        visited = set()

        while current_idx != 0xFFFFFFFF and current_idx not in visited:
            visited.add(current_idx)
            page_data = self.read_page(current_idx)
            if not page_data: 
                break

            try:
                page = PDBPage(page_data, current_idx)
                num_rows = struct.unpack_from('<H', page.data, 26)[0] & 0x1FFF
                
                # Offset Scavenger: collect all row offsets
                offsets = []
                for i in range(num_rows):
                    ofs_pos = 4096 - 6 - (2*i)
                    if ofs_pos < 0: break
                    row_offset = struct.unpack_from('<H', page.data, ofs_pos)[0]
                    if 32 <= row_offset < 4096:
                        offsets.append(row_offset)
                
                for row_offset in offsets:
                    if row_offset < 4096:
                        row = page.data[row_offset:]
                        t_id = struct.unpack_from('<I', row, 0)[0]
                        
                        if t_id in target_ids:
                            meta = self._extract_track_meta(row)
                            meta['id'] = t_id
                            results[t_id] = meta
                        
            except Exception as e:
                pass

            next_p = struct.unpack_from('<I', page_data, 12)[0]
            if next_p == current_idx or next_p == 0: break
            current_idx = next_p

        return results

    def _extract_track_meta(self, row: bytes) -> Dict:
        """Extract track metadata from a row."""
        meta = {
            'title': '',
            'artist': '',
            'path': '',
            'bpm': 0.0
        }
        
        try:
            # Scan for strings in the row
            pattern = re.compile(b'[ -~]{3,200}')
            strings = []
            for match in pattern.finditer(row[:min(len(row), 500)]):
                text = match.group().decode('utf-8', errors='ignore').strip()
                if len(text) >= 3:
                    strings.append(text)
            
            # Heuristic assignment
            if len(strings) >= 1:
                meta['title'] = strings[0]
            if len(strings) >= 2:
                meta['artist'] = strings[1]
            if len(strings) >= 3:
                # Path is usually longer
                for s in strings:
                    if '/' in s or '\\' in s or len(s) > 20:
                        meta['path'] = s
                        break
            
            # Try to extract BPM (usually a float near the beginning)
            for i in range(0, min(len(row) - 4, 100), 4):
                try:
                    val = struct.unpack_from('<f', row, i)[0]
                    if 60.0 <= val <= 200.0:  # Reasonable BPM range
                        meta['bpm'] = val
                        break
                except:
                    pass
                    
        except Exception:
            pass
            
        return meta
