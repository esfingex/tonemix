"""
Security utilities for ToneMix
"""
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE_MB = 500  # Maximum audio file size in MB
MAX_PLAYLIST_NAME_LENGTH = 255
MAX_TRACK_TITLE_LENGTH = 500
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aiff', '.flac', '.m4a'}


def validate_audio_file(file_path: str) -> bool:
    """
    Validate audio file for security concerns
    
    Args:
        file_path: Path to audio file
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If file is invalid
    """
    path = Path(file_path)
    
    # Check if file exists
    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    # Check extension
    if path.suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    
    # Check file size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
    
    return True


def validate_playlist_name(name: str) -> bool:
    """
    Validate playlist name
    
    Args:
        name: Playlist name
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If name is invalid
    """
    if not name or not name.strip():
        raise ValueError("Playlist name cannot be empty")
    
    if len(name) > MAX_PLAYLIST_NAME_LENGTH:
        raise ValueError(f"Playlist name too long (max {MAX_PLAYLIST_NAME_LENGTH} chars)")
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    dangerous_chars = ['/', '\\', '..', '\0']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    return sanitized
