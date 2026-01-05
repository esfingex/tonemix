"""
Audio analysis engine using Essentia and Librosa
"""
import numpy as np
import librosa
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

# Essentia imports (will be installed via requirements.txt)
try:
    import essentia
    import essentia.standard as es
    ESSENTIA_AVAILABLE = True
except ImportError:
    ESSENTIA_AVAILABLE = False
    logging.warning("Essentia not available. Install with: pip install essentia")

from src.core.audio_processor import AudioProcessor
from src.utils.camelot import musical_to_camelot
from src.utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class TrackAnalysis:
    """Data class for track analysis results"""
    key_musical: str
    key_camelot: str
    bpm: float
    energy_level: float
    duration_seconds: float
    waveform_data: np.ndarray


class AudioAnalyzer:
    """Audio analysis engine using Essentia and Librosa"""
    
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.key_profile = config.analysis.get('key_profile', 'edma')
        self.energy_weights = config.analysis.get('energy_weights', {'rms': 0.6, 'spectral_centroid': 0.4})
        
        if not ESSENTIA_AVAILABLE:
            logger.warning("Essentia not available - key and BPM detection will be limited")
    
    def analyze_track(self, file_path: str) -> Optional[TrackAnalysis]:
        """
        Perform complete audio analysis on a track
        
        Args:
            file_path: Path to audio file
            
        Returns:
            TrackAnalysis object or None on error
        """
        try:
            logger.info(f"Analyzing track: {file_path}")
            
            # Load audio
            audio, sr = self.audio_processor.load_audio(file_path)
            if audio is None:
                return None
            
            # Extract features
            key_musical = self.extract_key(audio, sr)
            key_camelot = musical_to_camelot(key_musical) or "Unknown"
            bpm = self.extract_bpm(audio, sr)
            energy = self.calculate_energy(audio, sr)
            duration = len(audio) / sr
            
            # Generate waveform for visualization
            waveform = self.audio_processor.downsample_waveform(audio)
            
            result = TrackAnalysis(
                key_musical=key_musical,
                key_camelot=key_camelot,
                bpm=bpm,
                energy_level=energy,
                duration_seconds=duration,
                waveform_data=waveform
            )
            
            logger.info(f"Analysis complete: Key={key_camelot}, BPM={bpm:.1f}, Energy={energy:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing track {file_path}: {e}")
            return None
    
    def extract_key(self, audio: np.ndarray, sr: int) -> str:
        """
        Extract musical key using Essentia KeyExtractor
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            Musical key (e.g., "C major", "A minor")
        """
        if not ESSENTIA_AVAILABLE:
            logger.warning("Essentia not available - returning default key")
            return "C major"
        
        try:
            # Use Essentia KeyExtractor
            key_extractor = es.KeyExtractor(profileType=self.key_profile)
            key, scale, strength = key_extractor(audio.astype(np.float32))
            
            # Format key
            musical_key = f"{key} {scale}"
            
            logger.debug(f"Key detected: {musical_key} (strength: {strength:.2f})")
            return musical_key
            
        except Exception as e:
            logger.error(f"Error extracting key: {e}")
            return "C major"
    
    def extract_bpm(self, audio: np.ndarray, sr: int) -> float:
        """
        Extract BPM using Essentia RhythmExtractor
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            BPM value
        """
        if not ESSENTIA_AVAILABLE:
            # Fallback to librosa
            return self._extract_bpm_librosa(audio, sr)
        
        try:
            # Use Essentia RhythmExtractor2013
            rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
            bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio.astype(np.float32))
            
            logger.debug(f"BPM detected: {bpm:.2f} (confidence: {beats_confidence:.2f})")
            return float(bpm)
            
        except Exception as e:
            logger.error(f"Error extracting BPM with Essentia: {e}")
            return self._extract_bpm_librosa(audio, sr)
    
    def _extract_bpm_librosa(self, audio: np.ndarray, sr: int) -> float:
        """
        Fallback BPM extraction using librosa
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            BPM value
        """
        try:
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
            logger.debug(f"BPM detected (librosa): {tempo:.2f}")
            return float(tempo)
        except Exception as e:
            logger.error(f"Error extracting BPM with librosa: {e}")
            return 120.0  # Default BPM
    
    def calculate_energy(self, audio: np.ndarray, sr: int) -> float:
        """
        Calculate energy level (0-10 scale) based on RMS and Spectral Centroid
        
        Args:
            audio: Audio array
            sr: Sample rate
            
        Returns:
            Energy level (0-10)
        """
        try:
            # Calculate RMS energy
            rms = self.audio_processor.calculate_rms_energy(audio)
            
            # Calculate spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)
            spectral_centroid_mean = np.mean(spectral_centroids)
            
            # Normalize spectral centroid (typical range: 0-8000 Hz)
            spectral_centroid_normalized = min(spectral_centroid_mean / 8000.0, 1.0)
            
            # Weighted combination
            rms_weight = self.energy_weights['rms']
            centroid_weight = self.energy_weights['spectral_centroid']
            
            energy_raw = (rms * rms_weight) + (spectral_centroid_normalized * centroid_weight)
            
            # Scale to 0-10
            energy_scaled = self._normalize_to_scale(energy_raw, 0, 10)
            
            logger.debug(f"Energy calculated: {energy_scaled:.2f} (RMS: {rms:.3f}, Centroid: {spectral_centroid_mean:.1f})")
            return energy_scaled
            
        except Exception as e:
            logger.error(f"Error calculating energy: {e}")
            return 5.0  # Default mid-range energy
    
    def _normalize_to_scale(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalize value to a specific scale
        
        Args:
            value: Input value
            min_val: Minimum output value
            max_val: Maximum output value
            
        Returns:
            Normalized value
        """
        # Assuming input is roughly 0-1 range
        normalized = np.clip(value, 0, 1)
        scaled = normalized * (max_val - min_val) + min_val
        return float(scaled)
    
    def batch_analyze(self, file_paths: list[str], progress_callback=None) -> Dict[str, TrackAnalysis]:
        """
        Analyze multiple tracks
        
        Args:
            file_paths: List of file paths
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping file paths to TrackAnalysis results
        """
        results = {}
        total = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            try:
                result = self.analyze_track(file_path)
                if result:
                    results[file_path] = result
                
                if progress_callback:
                    progress_callback(i + 1, total)
                    
            except Exception as e:
                logger.error(f"Error in batch analysis for {file_path}: {e}")
        
        return results
