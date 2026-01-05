"""
Camelot Wheel key conversion utilities
"""
from typing import Optional, Tuple


# Complete Camelot Wheel mapping
CAMELOT_MAP = {
    # Minor keys (A)
    'C minor': '5A', 'Cm': '5A',
    'C# minor': '12A', 'C#m': '12A', 'Db minor': '12A', 'Dbm': '12A',
    'D minor': '7A', 'Dm': '7A',
    'D# minor': '2A', 'D#m': '2A', 'Eb minor': '2A', 'Ebm': '2A',
    'E minor': '9A', 'Em': '9A',
    'F minor': '4A', 'Fm': '4A',
    'F# minor': '11A', 'F#m': '11A', 'Gb minor': '11A', 'Gbm': '11A',
    'G minor': '6A', 'Gm': '6A',
    'G# minor': '1A', 'G#m': '1A', 'Ab minor': '1A', 'Abm': '1A',
    'A minor': '8A', 'Am': '8A',
    'A# minor': '3A', 'A#m': '3A', 'Bb minor': '3A', 'Bbm': '3A',
    'B minor': '10A', 'Bm': '10A',
    
    # Major keys (B)
    'C major': '8B', 'C': '8B',
    'C# major': '3B', 'C#': '3B', 'Db major': '3B', 'Db': '3B',
    'D major': '10B', 'D': '10B',
    'D# major': '5B', 'D#': '5B', 'Eb major': '5B', 'Eb': '5B',
    'E major': '12B', 'E': '12B',
    'F major': '7B', 'F': '7B',
    'F# major': '2B', 'F#': '2B', 'Gb major': '2B', 'Gb': '2B',
    'G major': '9B', 'G': '9B',
    'G# major': '4B', 'G#': '4B', 'Ab major': '4B', 'Ab': '4B',
    'A major': '11B', 'A': '11B',
    'A# major': '6B', 'A#': '6B', 'Bb major': '6B', 'Bb': '6B',
    'B major': '1B', 'B': '1B',
}

# Reverse mapping (Camelot to musical notation)
MUSICAL_MAP = {v: k for k, v in CAMELOT_MAP.items() if 'major' in k or 'minor' in k}


def musical_to_camelot(key: str) -> Optional[str]:
    """
    Convert musical key notation to Camelot format
    
    Args:
        key: Musical key (e.g., 'C major', 'Am', 'F#m')
        
    Returns:
        Camelot key (e.g., '8B', '8A') or None if not found
    """
    return CAMELOT_MAP.get(key)


def camelot_to_musical(camelot: str) -> Optional[str]:
    """
    Convert Camelot key to musical notation
    
    Args:
        camelot: Camelot key (e.g., '8B', '8A')
        
    Returns:
        Musical key (e.g., 'C major', 'A minor') or None if not found
    """
    return MUSICAL_MAP.get(camelot)


def get_compatible_keys(camelot: str) -> list[str]:
    """
    Get harmonically compatible keys for mixing
    
    Args:
        camelot: Camelot key (e.g., '8B')
        
    Returns:
        List of compatible Camelot keys
    """
    if not camelot or len(camelot) < 2:
        return []
    
    try:
        number = int(camelot[:-1])
        letter = camelot[-1]
    except (ValueError, IndexError):
        return []
    
    compatible = []
    
    # Same key
    compatible.append(camelot)
    
    # Adjacent keys (+1, -1)
    next_num = (number % 12) + 1
    prev_num = ((number - 2) % 12) + 1
    compatible.append(f"{next_num}{letter}")
    compatible.append(f"{prev_num}{letter}")
    
    # Relative major/minor
    other_letter = 'B' if letter == 'A' else 'A'
    compatible.append(f"{number}{other_letter}")
    
    # Energy boost/drop (same letter, +/-1)
    compatible.append(f"{next_num}{letter}")
    compatible.append(f"{prev_num}{letter}")
    
    return list(set(compatible))  # Remove duplicates


def get_key_color(camelot: str) -> Tuple[int, int, int]:
    """
    Get RGB color for Camelot key (for UI visualization)
    
    Args:
        camelot: Camelot key (e.g., '8B')
        
    Returns:
        RGB tuple (r, g, b)
    """
    color_map = {
        # Minor keys (A) - darker tones
        '1A': (255, 100, 100),   # Red
        '2A': (255, 150, 100),   # Orange
        '3A': (255, 200, 100),   # Yellow-orange
        '4A': (255, 250, 100),   # Yellow
        '5A': (200, 255, 100),   # Yellow-green
        '6A': (150, 255, 100),   # Light green
        '7A': (100, 255, 150),   # Green
        '8A': (100, 255, 200),   # Green-cyan
        '9A': (100, 250, 255),   # Cyan
        '10A': (100, 200, 255),  # Cyan-blue
        '11A': (100, 150, 255),  # Blue
        '12A': (150, 100, 255),  # Purple
        
        # Major keys (B) - lighter tones
        '1B': (255, 130, 130),
        '2B': (255, 170, 130),
        '3B': (255, 210, 130),
        '4B': (255, 255, 130),
        '5B': (210, 255, 130),
        '6B': (170, 255, 130),
        '7B': (130, 255, 170),
        '8B': (130, 255, 210),
        '9B': (130, 250, 255),
        '10B': (130, 210, 255),
        '11B': (130, 170, 255),
        '12B': (170, 130, 255),
    }
    
    return color_map.get(camelot, (100, 100, 100))  # Default gray


def normalize_key_notation(key: str) -> str:
    """
    Normalize key notation to standard format
    
    Args:
        key: Key in any format
        
    Returns:
        Normalized key notation
    """
    # Convert to title case
    key = key.strip().title()
    
    # Standardize sharp/flat notation
    key = key.replace('Sharp', '#').replace('Flat', 'b')
    
    return key
