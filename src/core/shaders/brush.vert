#version 330 core
// brush.vert - Vertex Shader for High Performance Brush Splatting

layout(location = 0) in vec2 aPosition; // Quad vertices (-1..1)
layout(location = 1) in vec2 aTexCoord; // UVs (0..1)

uniform mat4 uMVP;       // Projection * View Matrix
uniform vec2 uPos;       // Mouse Position (Canvas Coords)
uniform float uSize;     // Brush Size (Pressure Modulated)
uniform float uRotation; // Rotation Jitter (Radians)

uniform vec2 uCanvasSize; // Total canvas dimensions in pixels

out vec2 vUV;
out vec2 vCanvasCoords;  

void main() {
    // 1. Scale Quad (Brush radius)
    vec2 scaled = aPosition * (uSize * 0.5);
    
    // 2. Rotate Quad
    float s = sin(uRotation);
    float c = cos(uRotation);
    mat2 rotMat = mat2(c, -s, s, c);
    vec2 rotated = rotMat * scaled;
    
    // 3. Translate to Mouse Pos (Global Canvas Space)
    vec2 finalPos = rotated + uPos;
    
    // 4. Project to Clip Space
    gl_Position = uMVP * vec4(finalPos, 0.0, 1.0);
    
    // Pass data
    vUV = aTexCoord;
    // Normalize global coords for sampling background/paper textures
    vCanvasCoords = finalPos / uCanvasSize; 
}
