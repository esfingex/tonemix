#version 330 core

layout(location = 0) in float amplitude;  // Combined amplitude
layout(location = 1) in float low;        // Bass amplitude
layout(location = 2) in float mid;        // Mid amplitude  
layout(location = 3) in float high;       // High amplitude

uniform float width;        // Widget width in pixels
uniform float height;       // Widget height in pixels
uniform float zoom;         // Visible window in seconds
uniform float playhead;     // Playhead position (0-1)
uniform float duration;     // Track duration in seconds
uniform int num_samples;    // Total number of samples

out vec3 spectral;  // Pass (low, mid, high) to fragment shader

void main() {
    // Each sample generates 2 vertices (top and bottom of bar)
    int sample_index = gl_VertexID / 2;
    int vertex_type = gl_VertexID % 2;  // 0 = bottom, 1 = top
    
    // Calculate normalized position (0-1) based on sample index
    float normalized_pos = float(sample_index) / float(num_samples);
    
    // Convert to NDC coordinates [-1, 1]
    float x = normalized_pos * 2.0 - 1.0;
    
    // Y position: 0 for bottom vertex, amplitude for top vertex
    float y = (vertex_type == 0) ? 0.0 : amplitude * 0.9;
    
    // Output vertex position
    gl_Position = vec4(x, y, 0.0, 1.0);
    
    // Pass spectral data to fragment shader
    spectral = vec3(low, mid, high);
}
