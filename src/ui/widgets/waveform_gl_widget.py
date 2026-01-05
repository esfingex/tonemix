"""
GPU-accelerated waveform widget using OpenGL
"""
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader, QOpenGLBuffer, QOpenGLVertexArrayObject
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QSurfaceFormat
from OpenGL import GL
import numpy as np
import logging
import os
import ctypes

logger = logging.getLogger(__name__)


class WaveformGLWidget(QOpenGLWidget):
    """OpenGL-accelerated waveform visualization"""
    
    seek_requested = Signal(float)  # Emits position (0.0 - 1.0)
    
    def __init__(self, parent=None):
        # Set OpenGL format before creating widget
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        fmt.setSamples(4)  # 4x MSAA
        QSurfaceFormat.setDefaultFormat(fmt)
        
        super().__init__(parent)
        
        self.waveform_data = None
        self.playhead_position = 0.0
        self.duration = 0.0
        
        # Track metadata
        self.track_key = None
        self.track_bpm = None
        
        # Preferences
        self.preferences = {
            'color_scheme': 0,
            'show_artwork': True,
            'show_key': False,
            'show_bpm': False,
            'intensity': 1.0
        }
        
        # Zoom/Scroll
        self.visible_window = 10.0
        self.scrolling = True
        
        # OpenGL objects
        self.shader_program = None
        self.vbo = None
        self.vao = None
        self.num_vertices = 0
        
        # Settings
        self.setMinimumHeight(120)
        self.setMouseTracking(True)
        
        # Auto-update for playhead animation
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(16)  # ~60 FPS
    
    def set_preferences(self, prefs):
        """Set waveform preferences"""
        self.preferences.update(prefs)
        self.update()
    
    def set_waveform(self, waveform_data: np.ndarray, duration: float = 0.0, key: str = None, bpm: float = None, energy: int = None):
        """Set waveform data and upload to GPU"""
        self.waveform_data = waveform_data
        self.duration = duration
        self.track_key = key
        self.track_bpm = bpm
        self.playhead_position = 0.0
        
        self.visible_window = 10.0
        self.scrolling = True
        
        # Upload to GPU if OpenGL is initialized
        if self.shader_program:
            self._upload_waveform_to_gpu()
        
        self.update()
    
    def set_playhead_position(self, position: float):
        """Set playhead position (0.0 to 1.0)"""
        self.playhead_position = max(0.0, min(1.0, position))
        # Update happens automatically via timer
    
    def mousePressEvent(self, event):
        """Handle mouse click to seek"""
        if event.button() == Qt.LeftButton:
            x = event.pos().x()
            width = self.width()
            if width <= 0:
                return

            if self.scrolling and self.duration > 0:
                center_x = width / 2
                offset_x = x - center_x
                pps = width / self.visible_window
                offset_seconds = offset_x / pps
                current_seconds = self.playhead_position * self.duration
                new_seconds = current_seconds + offset_seconds
                new_position = new_seconds / self.duration
                new_position = max(0.0, min(1.0, new_position))
                self.seek_requested.emit(new_position)
                self.set_playhead_position(new_position)
            else:
                position = max(0.0, min(1.0, x / width))
                self.seek_requested.emit(position)
                self.set_playhead_position(position)
    
    def wheelEvent(self, event):
        """Handle scroll wheel for zooming"""
        factor = 1.1 if event.angleDelta().y() < 0 else 0.9
        self.visible_window = max(1.0, min(60.0, self.visible_window * factor))
        self.update()
    
    def initializeGL(self):
        """Initialize OpenGL resources"""
        try:
            logger.info("Initializing OpenGL for waveform rendering")
            
            # Create shader program
            self.shader_program = QOpenGLShaderProgram(self)
            
            # Load shaders
            shader_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'shaders')
            vert_path = os.path.join(shader_dir, 'waveform.vert')
            frag_path = os.path.join(shader_dir, 'waveform.frag')
            
            if not self.shader_program.addShaderFromSourceFile(QOpenGLShader.Vertex, vert_path):
                logger.error(f"Failed to compile vertex shader: {self.shader_program.log()}")
                return
            
            if not self.shader_program.addShaderFromSourceFile(QOpenGLShader.Fragment, frag_path):
                logger.error(f"Failed to compile fragment shader: {self.shader_program.log()}")
                return
            
            if not self.shader_program.link():
                logger.error(f"Failed to link shader program: {self.shader_program.log()}")
                return
            
            logger.info("Shaders compiled and linked successfully")
            
            # Create VAO and VBO
            self.vao = QOpenGLVertexArrayObject(self)
            self.vao.create()
            
            self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            self.vbo.create()
            
            # Upload waveform if already set
            if self.waveform_data is not None:
                self._upload_waveform_to_gpu()
            
        except Exception as e:
            logger.error(f"Error initializing OpenGL: {e}", exc_info=True)
    
    def _upload_waveform_to_gpu(self):
        """Upload waveform data to GPU VBO"""
        if self.waveform_data is None:
            return
        
        try:
            # Extract spectral data
            if isinstance(self.waveform_data, dict):
                low = np.array(self.waveform_data.get('low', []), dtype=np.float32)
                mid = np.array(self.waveform_data.get('mid', []), dtype=np.float32)
                high = np.array(self.waveform_data.get('high', []), dtype=np.float32)
            else:
                # Simple waveform - use as low frequency
                low = np.array(self.waveform_data, dtype=np.float32)
                mid = np.zeros_like(low)
                high = np.zeros_like(low)
            
            # Calculate combined amplitude
            amplitude = np.maximum(np.maximum(low, mid), high)
            
            # Create interleaved vertex data
            # Format: [amplitude, low, mid, high] per vertex
            num_samples = len(low)
            vertex_data = np.zeros(num_samples * 4, dtype=np.float32)
            
            for i in range(num_samples):
                vertex_data[i*4 + 0] = amplitude[i]
                vertex_data[i*4 + 1] = low[i]
                vertex_data[i*4 + 2] = mid[i]
                vertex_data[i*4 + 3] = high[i]
            
            # Bind VBO and upload data
            self.vbo.bind()
            self.vbo.allocate(vertex_data.tobytes(), vertex_data.nbytes)
            
            # Make context current for PyOpenGL
            self.makeCurrent()
            
            # Use Qt's shader program methods for attribute setup
            self.shader_program.enableAttributeArray(0)  # amplitude
            self.shader_program.enableAttributeArray(1)  # low
            self.shader_program.enableAttributeArray(2)  # mid
            self.shader_program.enableAttributeArray(3)  # high
            
            stride = 4 * 4  # 4 floats * 4 bytes
            from PySide6.QtOpenGL import QOpenGLBuffer
            
            self.shader_program.setAttributeBuffer(0, int(GL.GL_FLOAT), 0, 1, stride)
            self.shader_program.setAttributeBuffer(1, int(GL.GL_FLOAT), 4, 1, stride)
            self.shader_program.setAttributeBuffer(2, int(GL.GL_FLOAT), 8, 1, stride)
            self.shader_program.setAttributeBuffer(3, int(GL.GL_FLOAT), 12, 1, stride)
            
            self.vbo.release()
            self.vao.release()
            
            self.num_vertices = num_samples
            logger.info(f"Uploaded {num_samples} samples to GPU")
            
        except Exception as e:
            logger.error(f"Error uploading waveform to GPU: {e}", exc_info=True)
    
    def paintGL(self):
        """Render waveform using OpenGL"""
        if not self.shader_program or self.num_vertices == 0:
            return
        
        try:
            # Make context current for PyOpenGL
            self.makeCurrent()
            
            # Clear screen using PyOpenGL
            GL.glClearColor(0.16, 0.16, 0.16, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            
            # Enable blending
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            
            # Bind shader
            self.shader_program.bind()
            
            # Set uniforms using location IDs
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("width"), float(self.width()))
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("height"), float(self.height()))
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("zoom"), self.visible_window)
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("playhead"), self.playhead_position)
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("duration"), self.duration)
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("num_samples"), self.num_vertices)
            self.shader_program.setUniformValue(self.shader_program.uniformLocation("intensity"), self.preferences.get('intensity', 1.0))
            
            # Bind VAO and draw using PyOpenGL
            # Each sample becomes 2 vertices (top and bottom of bar)
            self.vao.bind()
            GL.glDrawArrays(GL.GL_LINES, 0, self.num_vertices * 2)
            self.vao.release()
            
            self.shader_program.release()
            
        except Exception as e:
            logger.error(f"Error in paintGL: {e}", exc_info=True)
    
    def resizeGL(self, w, h):
        """Handle widget resize"""
        gl = self.context().functions()
        gl.glViewport(0, 0, w, h)
    
    def clear(self):
        """Clear waveform"""
        self.waveform_data = None
        self.playhead_position = 0.0
        self.track_key = None
        self.track_bpm = None
        self.num_vertices = 0
        self.update()
