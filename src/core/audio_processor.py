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

    def get_artwork(self, file_path: str) -> Optional[bytes]:
        """
        Extract artwork from audio file
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Bytes of image data or None
        """
        try:
            import mutagen
            from mutagen.flac import FLAC
            from mutagen.id3 import ID3, APIC
            from mutagen.mp3 import MP3
            
            path = Path(file_path)
            suffix = path.suffix.lower()
            
            if suffix == '.flac':
                audio = FLAC(file_path)
                if audio.pictures:
                    return audio.pictures[0].data
                    
            elif suffix == '.mp3':
                audio = MP3(file_path, ID3=ID3)
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        return tag.data
                        
            # TODO: Add other formats if needed
            
            return None
        except Exception as e:
            logger.error(f"Error extracting artwork from {file_path}: {e}")
            return None
    
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
    
    def generate_spectral_waveform(self, audio: np.ndarray, sample_rate: int, target_points: int = None) -> dict:
        """
        Generate spectral waveform with frequency bands (Rekordbox-style)
        
        Args:
            audio: Full audio array
            sample_rate: Sample rate of audio
            target_points: Target number of points
            
        Returns:
            Dictionary with 'low', 'mid', 'high' frequency band arrays
        """
        if target_points is None:
            target_points = self.waveform_points
        
        try:
            from scipy import signal
            
            # Calculate chunk size
            chunk_size = len(audio) // target_points
            if chunk_size < 1:
                chunk_size = 1
            
            # Initialize band arrays
            low_band = []
            mid_band = []
            high_band = []
            
            # Process in chunks
            for i in range(0, len(audio), chunk_size):
                chunk = audio[i:i+chunk_size]
                if len(chunk) < 64:  # Too small for FFT
                    low_band.append(np.max(np.abs(chunk)))
                    mid_band.append(np.max(np.abs(chunk)))
                    high_band.append(np.max(np.abs(chunk)))
                    continue
                
                # Perform FFT
                fft = np.fft.rfft(chunk)
                freqs = np.fft.rfftfreq(len(chunk), 1/sample_rate)
                magnitudes = np.abs(fft)
                
                # Define frequency bands (Hz)
                # Low: 20-250 Hz (bass)
                # Mid: 250-4000 Hz (vocals, melody)
                # High: 4000-20000 Hz (cymbals, hi-hats)
                low_mask = (freqs >= 20) & (freqs < 250)
                mid_mask = (freqs >= 250) & (freqs < 4000)
                high_mask = (freqs >= 4000) & (freqs < 20000)
                
                # Get max magnitude for each band
                low_band.append(np.max(magnitudes[low_mask]) if np.any(low_mask) else 0)
                mid_band.append(np.max(magnitudes[mid_mask]) if np.any(mid_mask) else 0)
                high_band.append(np.max(magnitudes[high_mask]) if np.any(high_mask) else 0)
            
            # Convert to numpy arrays and normalize
            low_band = np.array(low_band[:target_points])
            mid_band = np.array(mid_band[:target_points])
            high_band = np.array(high_band[:target_points])
            
            # Normalize each band
            if np.max(low_band) > 0:
                low_band = low_band / np.max(low_band)
            if np.max(mid_band) > 0:
                mid_band = mid_band / np.max(mid_band)
            if np.max(high_band) > 0:
                high_band = high_band / np.max(high_band)
            
            logger.debug(f"Generated spectral waveform: {len(low_band)} points")
            
            return {
                'low': low_band,
                'mid': mid_band,
                'high': high_band
            }
            
        except Exception as e:
            logger.error(f"Error generating spectral waveform: {e}")
            # Fallback to simple waveform
            simple = self.downsample_waveform(audio, target_points)
            return {
                'low': simple,
                'mid': simple,
                'high': simple
            }
    
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
    
    def waveform_to_bytes(self, waveform) -> bytes:
        """
        Convert waveform (array or dict) to bytes for database storage
        
        Args:
            waveform: Waveform array or dictionary
            
        Returns:
            Bytes representation
        """
        import pickle
        try:
            return pickle.dumps(waveform)
        except Exception as e:
            logger.error(f"Error pickling waveform: {e}")
            return b""
    
    def bytes_to_waveform(self, data: bytes):
        """
        Convert bytes back to waveform (array or dict)
        
        Args:
            data: Bytes data
            
        Returns:
            Waveform array or dictionary
        """
        import pickle
        try:
            return pickle.loads(data)
        except Exception as e:
            # Fallback for old flat binary format
            try:
                return np.frombuffer(data, dtype=np.float32)
            except Exception as e2:
                logger.error(f"Error unpickling waveform: {e}, fallback failed: {e2}")
                return np.array([])
