"""
Database models for ToneMix
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, LargeBinary, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Track(Base):
    """Track model for music library"""
    
    __tablename__ = 'tracks'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic metadata
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), index=True)
    album = Column(String(255))
    genre = Column(String(100))
    year = Column(Integer)
    
    # Analysis results
    key_camelot = Column(String(3), index=True)  # e.g., "8A", "12B"
    key_musical = Column(String(10))  # e.g., "C major", "Am"
    bpm = Column(Float, index=True)
    energy_level = Column(Float, index=True)  # 0-10 scale
    
    # File information
    file_path = Column(String(512), unique=True, nullable=False, index=True)
    file_format = Column(String(10))  # FLAC, AIFF, MP3, WAV, M4A
    duration_seconds = Column(Float)
    file_size_bytes = Column(BigInteger)
    bitrate = Column(Integer)
    sample_rate = Column(Integer)
    
    # Waveform data (stored as binary for fast loading)
    waveform_data = Column(LargeBinary)  # Downsampled waveform (~2000 points)
    
    # Transcoding status
    transcoded_path = Column(String(512))  # Path to AIFF if transcoded
    is_transcoded = Column(Boolean, default=False)
    
    # User data
    rating = Column(Integer, default=0)  # 0-5 stars
    comment = Column(String(500))
    cue_points = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    analyzed_at = Column(DateTime)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Rekordbox integration
    exported_to_rekordbox = Column(Boolean, default=False)
    rekordbox_id = Column(String(50))
    last_exported_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Track(id={self.id}, title='{self.title}', artist='{self.artist}', key={self.key_camelot}, bpm={self.bpm})>"
    
    def to_dict(self):
        """Convert track to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'genre': self.genre,
            'year': self.year,
            'key_camelot': self.key_camelot,
            'key_musical': self.key_musical,
            'bpm': self.bpm,
            'energy_level': self.energy_level,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'duration_seconds': self.duration_seconds,
            'rating': self.rating,
            'comment': self.comment,
            'is_transcoded': self.is_transcoded,
            'transcoded_path': self.transcoded_path,
        }


class Playlist(Base):
    """Playlist model"""
    
    __tablename__ = 'playlists'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    icon = Column(String(50))  # Emoji or icon name
    
    # Smart playlist filters (JSON stored as string)
    is_smart = Column(Boolean, default=False)
    filter_rules = Column(String(1000))  # JSON string with filter rules
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Playlist(id={self.id}, name='{self.name}')>"


class PlaylistTrack(Base):
    """Many-to-many relationship between playlists and tracks"""
    
    __tablename__ = 'playlist_tracks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    position = Column(Integer, default=0)  # Order in playlist
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<PlaylistTrack(playlist_id={self.playlist_id}, track_id={self.track_id})>"
