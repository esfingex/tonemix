#version 330 core

in vec3 spectral;      // (low, mid, high) from vertex shader
in float bar_height;

out vec4 fragColor;

uniform float intensity;  // Color intensity multiplier (0-1)

void main() {
    // Normalize each frequency band independently
    // This is the key difference from CPU rendering - each band contributes fully
    float low_norm = spectral.x;
    float mid_norm = spectral.y;
    float high_norm = spectral.z;
    
    // Find max for normalization
    float max_val = max(max(low_norm, mid_norm), high_norm);
    if (max_val > 0.0) {
        low_norm /= max_val;
        mid_norm /= max_val;
        high_norm /= max_val;
    }
    
    // Pure RGB additive mixing (Mixxx style)
    // Blue = Bass, Green = Mids, Red = Highs
    vec3 color;
    color.r = high_norm * intensity;  // Red channel = Highs
    color.g = mid_norm * intensity;   // Green channel = Mids
    color.b = low_norm * intensity;   // Blue channel = Lows
    
    // Boost overall brightness
    color *= 1.5;
    color = clamp(color, 0.0, 1.0);
    
    // Output final color with slight transparency
    fragColor = vec4(color, 0.85);
}
