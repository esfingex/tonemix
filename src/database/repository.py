"""
Repository pattern for database operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
import logging

from src.database.models import Track, Playlist, PlaylistTrack
from src.database.connection import get_session

logger = logging.getLogger(__name__)


class TrackRepository:
    """Repository for Track operations"""
    
    @staticmethod
    def create(track_data: Dict[str, Any]) -> Optional[Track]:
        """Create a new track"""
        try:
            with get_session() as session:
                track = Track(**track_data)
                session.add(track)
                session.flush()
                session.refresh(track)
                return track
        except Exception as e:
            logger.error(f"Error creating track: {e}")
            return None
    
    @staticmethod
    def get_by_id(track_id: int) -> Optional[Track]:
        """Get track by ID"""
        try:
            with get_session() as session:
                session.expire_on_commit = False
                return session.query(Track).filter(Track.id == track_id).first()
        except Exception as e:
            logger.error(f"Error getting track by ID: {e}")
            return None
    
    @staticmethod
    def get_by_path(file_path: str) -> Optional[Track]:
        """Get track by file path"""
        try:
            with get_session() as session:
                return session.query(Track).filter(Track.file_path == file_path).first()
        except Exception as e:
            logger.error(f"Error getting track by path: {e}")
            return None

    @staticmethod
    def get_by_paths(file_paths: List[str]) -> Dict[str, Track]:
        """Get multiple tracks by paths. Returns dict {path: Track}"""
        if not file_paths:
            return {}
        try:
            with get_session() as session:
                # Process in chunks to avoid SQLite limits if necessary
                tracks = session.query(Track).filter(Track.file_path.in_(file_paths)).all()
                return {t.file_path: t for t in tracks}
        except Exception as e:
            logger.error(f"Error getting tracks by paths: {e}")
            return {}

    
    @staticmethod
    def get_all(limit: int = None, offset: int = 0) -> List[Track]:
        """Get all tracks with optional pagination"""
        try:
            with get_session() as session:
                session.expire_on_commit = False
                query = session.query(Track).order_by(Track.created_at.asc())
                if limit:
                    query = query.limit(limit).offset(offset)
                return query.all()
        except Exception as e:
            logger.error(f"Error getting all tracks: {e}")
            return []
    
    @staticmethod
    def search(query: str) -> List[Track]:
        """Search tracks by title, artist, or album"""
        try:
            with get_session() as session:
                search_pattern = f"%{query}%"
                return session.query(Track).filter(
                    or_(
                        Track.title.ilike(search_pattern),
                        Track.artist.ilike(search_pattern),
                        Track.album.ilike(search_pattern)
                    )
                ).all()
        except Exception as e:
            logger.error(f"Error searching tracks: {e}")
            return []
    
    @staticmethod
    def filter_by(filters: Dict[str, Any]) -> List[Track]:
        """
        Filter tracks by multiple criteria
        
        Example:
            filter_by({'key_camelot': '8A', 'bpm': (120, 130)})
        """
        try:
            with get_session() as session:
                query = session.query(Track)
                
                for key, value in filters.items():
                    if hasattr(Track, key):
                        if isinstance(value, tuple) and len(value) == 2:
                            # Range filter (min, max)
                            query = query.filter(
                                and_(
                                    getattr(Track, key) >= value[0],
                                    getattr(Track, key) <= value[1]
                                )
                            )
                        else:
                            # Exact match
                            query = query.filter(getattr(Track, key) == value)
                
                return query.all()
        except Exception as e:
            logger.error(f"Error filtering tracks: {e}")
            return []
    
    @staticmethod
    def update(track_id: int, updates: Dict[str, Any]) -> Optional[Track]:
        """Update track"""
        try:
            with get_session() as session:
                track = session.query(Track).filter(Track.id == track_id).first()
                if track:
                    for key, value in updates.items():
                        if hasattr(track, key):
                            setattr(track, key, value)
                    session.flush()
                    session.refresh(track)
                    return track
                return None
        except Exception as e:
            logger.error(f"Error updating track: {e}")
            return None
    
    @staticmethod
    def delete(track_id: int) -> bool:
        """Delete track"""
        try:
            with get_session() as session:
                track = session.query(Track).filter(Track.id == track_id).first()
                if track:
                    session.delete(track)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting track: {e}")
            return False
    
    @staticmethod
    def count() -> int:
        """Get total track count"""
        try:
            with get_session() as session:
                return session.query(Track).count()
        except Exception as e:
            logger.error(f"Error counting tracks: {e}")
            return 0


class PlaylistRepository:
    """Repository for Playlist operations"""
    
    @staticmethod
    def create(name: str, description: str = "", icon: str = "🎵") -> Optional[Playlist]:
        """Create a new playlist"""
        try:
            with get_session() as session:
                playlist = Playlist(name=name, description=description, icon=icon)
                session.add(playlist)
                session.flush()
                session.refresh(playlist)
                return playlist
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None
    
    @staticmethod
    def get_all() -> List[Playlist]:
        """Get all playlists"""
        try:
            with get_session() as session:
                return session.query(Playlist).order_by(Playlist.name).all()
        except Exception as e:
            logger.error(f"Error getting playlists: {e}")
            return []
            
    @staticmethod
    def update(playlist_id: int, updates: Dict[str, Any]) -> Optional[Playlist]:
        """Update playlist"""
        try:
            with get_session() as session:
                playlist = session.query(Playlist).filter(Playlist.id == playlist_id).first()
                if not playlist:
                    return None
                    
                for key, value in updates.items():
                    if hasattr(playlist, key):
                        setattr(playlist, key, value)
                        
                session.flush()
                session.refresh(playlist)
                return playlist
        except Exception as e:
            logger.error(f"Error updating playlist: {e}")
            return None

    @staticmethod
    def delete(playlist_id: int) -> bool:
        """Delete playlist"""
        try:
            with get_session() as session:
                playlist = session.query(Playlist).filter(Playlist.id == playlist_id).first()
                if not playlist:
                    return False
                
                # Dependencies (PlaylistTracks) should cascade if configured, 
                # but manual cleanup is safer if not.
                # Assuming Cascade Delete is set in models or we delete manually.
                # Let's trust SQLAlchemy cascade or delete explicit tracks first?
                session.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete()
                
                session.delete(playlist)
                return True
        except Exception as e:
            logger.error(f"Error deleting playlist: {e}")
            return False
    
    @staticmethod
    def add_track(playlist_id: int, track_id: int) -> bool:
        """Add track to playlist"""
        try:
            with get_session() as session:
                # Check if already exists
                existing = session.query(PlaylistTrack).filter(
                    and_(
                        PlaylistTrack.playlist_id == playlist_id,
                        PlaylistTrack.track_id == track_id
                    )
                ).first()
                
                if existing:
                    return True  # Already in playlist
                
                # Get current max position
                max_pos = session.query(PlaylistTrack).filter(
                    PlaylistTrack.playlist_id == playlist_id
                ).count()
                
                # Add track
                playlist_track = PlaylistTrack(
                    playlist_id=playlist_id,
                    track_id=track_id,
                    position=max_pos
                )
                session.add(playlist_track)
                return True
        except Exception as e:
            logger.error(f"Error adding track to playlist: {e}")
            return False
    
    
    @staticmethod
    def remove_track(playlist_id: int, track_id: int) -> bool:
        """Remove track from playlist"""
        try:
            with get_session() as session:
                session.query(PlaylistTrack).filter(
                    and_(
                        PlaylistTrack.playlist_id == playlist_id,
                        PlaylistTrack.track_id == track_id
                    )
                ).delete()
                return True
        except Exception as e:
            logger.error(f"Error removing track from playlist: {e}")
            return False

    @staticmethod
    def get_tracks(playlist_id: int) -> List[Track]:
        """Get all tracks in a playlist"""
        try:
            with get_session() as session:
                # Prevent expiration so we can use objects after session closes
                session.expire_on_commit = False 
                return session.query(Track).join(
                    PlaylistTrack, Track.id == PlaylistTrack.track_id
                ).filter(
                    PlaylistTrack.playlist_id == playlist_id
                ).order_by(PlaylistTrack.position).all()
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {e}")
            return []
