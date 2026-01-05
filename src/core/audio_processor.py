"""
Audio file loading and preprocessing
"""
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional
import logging
from pathlib import Path

from src.utils.config import config

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio loading and preprocessing utilities"""
    
    def __init__(self):
        self.sample_rate = config.audio.get('sample_rate', 44100)
        self.waveform_points = config.audio.get('waveform_points', 2000)
    
    def load_audio(self, file_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """
        Load audio file and resample to target sample rate
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate) or (None, None) on error
        """
        try:
            # Load audio with librosa (automatically resamples)
            audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            logger.info(f"Loaded audio: {file_path} ({len(audio)} samples, {sr} Hz)")
            return audio, sr
            
        except Exception as e:
            logger.error(f"Error loading audio file {file_path}: {e}")
            return None, None
    
    def get_audio_info(self, file_path: str) -> dict:
        """
        Get audio file metadata without loading entire file
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio metadata
        """
        try:
            info = sf.info(file_path)
            file_size = Path(file_path).stat().st_size
            
            return {
                'duration_seconds': info.duration,
                'sample_rate': info.samplerate,
                'channels': info.channels,
                'file_format': info.format,
                'subtype': info.subtype,
                'file_size_bytes': file_size,
                'bitrate': int((file_size * 8) / info.duration) if info.duration > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting audio info for {file_path}: {e}")
            return {}
    
    def downsample_waveform(self, audio: np.ndarray, target_points: int = None) -> np.ndarray:
        """
        Downsample waveform for efficient visualization
        
        Args:
            audio: Full audio array
            target_points: Target number of points (default from config)
            
        Returns:
            Downsampled waveform array
        """
        if target_points is None:
            target_points = self.waveform_points
        
        try:
            # Calculate chunk size
            chunk_size = len(audio) // target_points
            
            if chunk_size < 1:
                # Audio is shorter than target points, return as is
                return np.abs(audio)
            
            # Reshape and take max of each chunk (for peak detection)
            num_chunks = len(audio) // chunk_size
            truncated = audio[:num_chunks * chunk_size]
            reshaped = truncated.reshape(num_chunks, chunk_size)
            
            # Take max absolute value of each chunk
            downsampled = np.max(np.abs(reshaped), axis=1)
            
            logger.debug(f"Downsampled waveform: {len(audio)} -> {len(downsampled)} points")
            return downsampled
            
        except Exception as e:
            logger.error(f"Error downsampling waveform: {e}")
            return np.abs(audio[:target_points])
    
    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to [-1, 1] range
        
        Args:
            audio: Audio array
            
        Returns:
            Normalized audio array
        """
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val
        return audio
    
    def calculate_rms_energy(self, audio: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) energy
        
        Args:
            audio: Audio array
            
        Returns:
            RMS energy value
        """
        return float(np.sqrt(np.mean(audio**2)))
    
    def waveform_to_bytes(self, waveform: np.ndarray) -> bytes:
        """
        Convert waveform array to bytes for database storage
        
        Args:
            waveform: Waveform array
            
        Returns:
            Bytes representation
        """
        return waveform.astype(np.float32).tobytes()
    
    def bytes_to_waveform(self, data: bytes) -> np.ndarray:
        """
        Convert bytes back to waveform array
        
        Args:
            data: Bytes data
            
        Returns:
            Waveform array
        """
        return np.frombuffer(data, dtype=np.float32)
