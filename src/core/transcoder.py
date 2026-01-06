"""
Audio transcoding using FFmpeg
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
from mutagen import File
from mutagen.id3 import ID3, TKEY, TIT2, TPE1, TALB, TDRC, APIC
from mutagen.aiff import AIFF
from mutagen.wave import WAVE

from src.utils.config import config

logger = logging.getLogger(__name__)


class AudioTranscoder:
    """FFmpeg-based audio transcoding"""
    
    def __init__(self):
        self.ffmpeg_path = config.transcoding.get('ffmpeg_path', 'ffmpeg')
        self.output_format = config.transcoding.get('output_format', 'aiff')
        self.bit_depth = config.transcoding.get('bit_depth', 24)
        self.preserve_metadata = config.transcoding.get('preserve_metadata', True)
    
    def transcode_file(self, input_path: str, output_path: str = None, format: str = 'aiff') -> Optional[str]:
        """
        Transcode audio file to specified format
        
        Args:
            input_path: Input file path
            output_path: Output file path (auto-generated if None)
            format: Target format (aiff, wav, mp3, flac)
            
        Returns:
            Output file path or None on error
        """
        try:
            # Generate output path if not provided
            if output_path is None:
                input_file = Path(input_path)
                output_path = str(input_file.parent / f"{input_file.stem}.{format}")
            
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-vn',       # Ignore video/artwork streams (prevents crashes with bad covers)
                '-map', '0:a:0', # Select first audio stream only
            ]
            
            # Format specific settings
            if format in ['aiff', 'wav']:
                cmd.extend(['-acodec', 'pcm_s24be' if format == 'aiff' else 'pcm_s24le'])
            elif format == 'mp3':
                cmd.extend(['-acodec', 'libmp3lame', '-b:a', '320k'])
            elif format == 'flac':
                cmd.extend(['-acodec', 'flac'])
            
            cmd.extend(['-f', format])
            
            # Preserve metadata
            if self.preserve_metadata:
                cmd.extend(['-map_metadata', '0'])
            
            # Output file (overwrite if exists)
            cmd.extend(['-y', output_path])
            
            logger.info(f"Transcoding {input_path} to {output_path} ({format})")
            
            # Run FFmpeg
            # Using DEVNULL for stdout to avoid buffer issues, capture stderr for errors
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            logger.info(f"Transcoding complete: {output_path}")
            
            # Post-process: preserve artwork and tags if target is AIFF/WAV
            if self.preserve_metadata and format in ['aiff', 'wav']:
                self.copy_metadata_and_artwork(input_path, output_path)
            
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
                # Determine format from config or default to aiff for batch method (legacy support)
                output_path = self.transcode_file(input_path, format=self.output_format)
                if output_path:
                    results[input_path] = output_path
                
                if progress_callback:
                    progress_callback(i + 1, total)
                    
            except Exception as e:
                logger.error(f"Error in batch transcoding for {input_path}: {e}")
        
        return results

    def copy_metadata_and_artwork(self, source_path: str, dest_path: str) -> bool:
        """
        Copy tags and artwork from source to destination with resizing
        """
        try:
            from PIL import Image
            import io
            
            source = File(source_path)
            dest = File(dest_path)
            
            if not source or not dest:
                return False
                
            # Ensure dest has tags
            if dest.tags is None:
                dest.add_tags()
                
            # Copy basic tags
            tag_map = {
                'title': TIT2,
                'artist': TPE1,
                'album': TALB,
                'date': TDRC,
                'genre': lambda v: from_str(v) if 'from_str' in globals() else None # Placeholder
            }
            
            # Helper to find key case-insensitively
            def get_tag_value(src, key_name):
                # Try exact match
                if key_name in src: return src[key_name]
                # Try uppercase (FLAC/Vorbis)
                if key_name.upper() in src: return src[key_name.upper()]
                # Try title case
                if key_name.title() in src: return src[key_name.title()]
                return None

            # Standard tags
            for key in ['title', 'artist', 'album', 'date', 'genre', 'composer', 'copyright', 'isrc']:
                val = get_tag_value(source, key)
                frame_class = globals().get(
                    {'title': 'TIT2', 'artist': 'TPE1', 'album': 'TALB', 'date': 'TDRC', 
                     'genre': 'TCON', 'composer': 'TCOM', 'copyright': 'TCOP', 'isrc': 'TSRC'}.get(key)
                )
                
                if val and frame_class:
                    if isinstance(val, list): val = val[0]
                    dest.tags.add(frame_class(encoding=3, text=str(val)))
            
            # Copy artwork with resizing
            pic_data = None
            mime = 'image/jpeg'
            
            # Extract from FLAC
            if hasattr(source, 'pictures') and source.pictures:
                pic_data = source.pictures[0].data
                mime = source.pictures[0].mime
            # Extract from ID3
            elif hasattr(source, 'tags'):
                for tag in source.tags.values():
                    if tag.__class__.__name__ == 'APIC':
                        pic_data = tag.data
                        mime = tag.mime
                        break
            
            if pic_data:
                try:
                    # Resize if too large
                    img = Image.open(io.BytesIO(pic_data))
                    
                    # If larger than 600x600, resize (Best for CDJs/Legacy)
                    max_size = 600
                    if img.width > max_size or img.height > max_size:
                        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        
                        # Save to new buffer
                        out_buffer = io.BytesIO()
                        # Convert to RGB to ensure JPEG compatibility
                        if img.mode in ('RGBA', 'P'): 
                            img = img.convert('RGB')
                        
                        img.save(out_buffer, format='JPEG', quality=85)
                        pic_data = out_buffer.getvalue()
                        mime = 'image/jpeg'
                        logger.info(f"Resized artwork to {img.size}")
                    
                    dest.tags.add(APIC(
                        encoding=3,
                        mime=mime,
                        type=3, 
                        desc=u'Cover',
                        data=pic_data
                    ))
                    logger.info("Artwork copied and optimized")
                    
                except Exception as img_err:
                    logger.warning(f"Failed to process artwork image: {img_err}")
                    # Fallback: try copying raw data if resize failed? 
                    # Probably better to skip to avoid crash
            
            dest.save()
            return True
            
        except Exception as e:
            logger.warning(f"Error copying metadata: {e}")
            import traceback
            traceback.print_exc()
            return False
