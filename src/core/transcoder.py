"""
Audio transcoding using FFmpeg
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from mutagen.id3 import ID3, TKEY
from mutagen.aiff import AIFF

from src.utils.config import config

logger = logging.getLogger(__name__)


class AudioTranscoder:
    """FFmpeg-based audio transcoding"""
    
    def __init__(self):
        self.ffmpeg_path = config.transcoding.get('ffmpeg_path', 'ffmpeg')
        self.output_format = config.transcoding.get('output_format', 'aiff')
        self.bit_depth = config.transcoding.get('bit_depth', 24)
        self.preserve_metadata = config.transcoding.get('preserve_metadata', True)
    
    def transcode_to_aiff(self, input_path: str, output_path: str = None) -> Optional[str]:
        """
        Transcode audio file to AIFF 24-bit
        
        Args:
            input_path: Input file path
            output_path: Output file path (auto-generated if None)
            
        Returns:
            Output file path or None on error
        """
        try:
            # Generate output path if not provided
            if output_path is None:
                input_file = Path(input_path)
                output_path = str(input_file.parent / f"{input_file.stem}.aiff")
            
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-acodec', 'pcm_s24be',  # 24-bit big-endian PCM
                '-f', 'aiff',
            ]
            
            # Preserve metadata
            if self.preserve_metadata:
                cmd.extend(['-map_metadata', '0'])
            
            # Output file (overwrite if exists)
            cmd.extend(['-y', output_path])
            
            logger.info(f"Transcoding {input_path} to {output_path}")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Transcoding complete: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Error transcoding file: {e}")
            return None
    
    def inject_id3_tags(self, aiff_path: str, tags: dict) -> bool:
        """
        Inject ID3 tags into AIFF file using Mutagen
        
        Args:
            aiff_path: Path to AIFF file
            tags: Dictionary of tags to inject (e.g., {'key': '8A'})
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open AIFF file
            audio = AIFF(aiff_path)
            
            # Add ID3 tag if not present
            if audio.tags is None:
                audio.add_tags()
            
            # Inject Initial Key tag
            if 'key' in tags:
                audio.tags.add(TKEY(encoding=3, text=tags['key']))
            
            # Save tags
            audio.save()
            
            logger.info(f"ID3 tags injected into {aiff_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error injecting ID3 tags: {e}")
            return False
    
    def batch_transcode(self, input_paths: list[str], progress_callback=None) -> dict[str, str]:
        """
        Transcode multiple files
        
        Args:
            input_paths: List of input file paths
            progress_callback: Optional callback function(current, total)
            
        Returns:
            Dictionary mapping input paths to output paths
        """
        results = {}
        total = len(input_paths)
        
        for i, input_path in enumerate(input_paths):
            try:
                output_path = self.transcode_to_aiff(input_path)
                if output_path:
                    results[input_path] = output_path
                
                if progress_callback:
                    progress_callback(i + 1, total)
                    
            except Exception as e:
                logger.error(f"Error in batch transcoding for {input_path}: {e}")
        
        return results
