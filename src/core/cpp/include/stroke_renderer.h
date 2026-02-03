#ifndef STROKE_RENDERER_H
#define STROKE_RENDERER_H

#include "gl_utils.h"
#include <memory> 

namespace artflow {

/**
 * StokeRenderer - Handles GPU rendering of brush strokes using custom shaders.
 * Implements the "Splatting" technique with GPU acceleration.
 */
class StrokeRenderer {
public:
    StrokeRenderer();
    virtual ~StrokeRenderer();

    // Initialize OpenGL resources (Shaders, VAO/VBO)
    // Must be called with a valid OpenGL context active
    bool initialize();

    // Upload brush tip texture (Stamp)
    // data assumed to be RGBA 8-bit
    void setBrushTip(const unsigned char* data, int width, int height);
    
    // Upload global paper texture
    void setPaperTexture(const unsigned char* data, int width, int height);

    // Start a rendering frame (sets viewport and projection)
    void beginFrame(int width, int height);
    
    // Finish rendering
    void endFrame();

    /**
     * Draw a single dab (stamp) on the GPU.
     */
    void drawDab(float x, float y, float size, float rotation, 
                 float r, float g, float b, float a, float hardness, float pressure, int mode);

    // Advanced: Draw with explicit source texture for Ping-Pong manual blending
    void drawDabPingPong(float x, float y, float size, float rotation, 
                         float r, float g, float b, float a, float hardness, float pressure, int mode,
                         unsigned int canvasTextureId, unsigned int wetMapTextureId = 0);

private:
    void createQuad();

    unsigned int m_program;
    unsigned int m_vao;
    unsigned int m_vbo;
    
    unsigned int m_brushTexture;
    unsigned int m_paperTexture;
    
    // Uniform Locations cache
    int m_uMVP;
    int m_uCanvasSize; 
    int m_uPos;
    int m_uSize;
    int m_uRotation;
    int m_uColor;
    int m_uHardness;
    int m_uMode;
    int m_uPressure;
    int m_uPaperTex;   
    int m_uCanvasTex; 
    int m_uWetMap;     
    
    float m_proj[16];
    bool m_isInitialized;
};

} // namespace artflow

#endif // STROKE_RENDERER_H
