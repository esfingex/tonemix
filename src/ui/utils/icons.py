"""
Icon utilities
"""
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt

def get_icon(name: str) -> QIcon:
    """
    Get QIcon by name (placeholder)
    Returns a generated colored icon based on name hash for now
    """
    # TODO: Implement proper icon loading
    pixmap = QPixmap(16, 16)
    hash_val = sum(ord(c) for c in name)
    color = QColor.fromHsl((hash_val * 30) % 360, 200, 150)
    pixmap.fill(color)
    return QIcon(pixmap)
