
import base64
import sys
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QPolygonF, QGuiApplication
from PySide6.QtCore import Qt, QPointF, QBuffer, QIODevice

app = QGuiApplication(sys.argv)

def create_arrow(direction='right'):
    size = 12
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(QColor(0,0,0,0)) # Transparent
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Color #a0a0a0 (Dim Gray)
    color = QColor("#a0a0a0")
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    
    if direction == 'right':
        # Triangle pointing right
        points = [QPointF(4, 3), QPointF(9, 6), QPointF(4, 9)]
    else:
        # Triangle pointing down
        points = [QPointF(3, 4), QPointF(6, 9), QPointF(9, 4)]
        
    painter.drawPolygon(points)
    painter.end()
    
    # Save to buffer
    ba = QBuffer()
    ba.open(QIODevice.WriteOnly)
    img.save(ba, "PNG")
    return base64.b64encode(ba.data()).decode('utf-8')

print("RIGHT_ARROW_B64 = " + create_arrow('right'))
print("DOWN_ARROW_B64 = " + create_arrow('down'))
