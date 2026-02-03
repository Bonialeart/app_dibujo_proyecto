/**
 * ArtFlow Studio - Renderer Header
 * OpenGL-based rendering for canvas content
 */

#pragma once

#include <cstdint>
#include <vector>
#include <memory>
#include "gl_utils.h"

namespace artflow {

// Forward declarations
class Layer;
struct Color;

/**
 * OpenGL Renderer for canvas content
 */
class Renderer {
public:
    Renderer(int width, int height);
    virtual ~Renderer();
    
    // Prevent copying
    Renderer(const Renderer&) = delete;
    Renderer& operator=(const Renderer&) = delete;
    
    // Frame rendering
    void beginFrame();
    void endFrame();
    
    // Drawing operations
    void drawBackground(const Color& color);
    void drawLayer(const Layer& layer);
    void drawLayerWithBlendMode(const Layer& layer, int blendMode);
    
    // Framebuffer access
    const uint8_t* getFramebufferData() const;
    void getFramebufferData(uint8_t* buffer, size_t bufferSize) const;
    void setBufferData(const uint8_t* buffer);
    
    // Resize
    void resize(int width, int height);

    // Ping-Pong Management
    void swapBuffers() { m_activeIdx = 1 - m_activeIdx; }
    unsigned int getTargetFBO() const { return m_fbo[m_activeIdx]; }
    unsigned int getSourceTexture() const { return m_tex[1 - m_activeIdx]; }
    
    // Dimensions
    int getWidth() const { return m_width; }
    int getHeight() const { return m_height; }

private:
    int m_width;
    int m_height;
    
    // OpenGL resources (Ping-Pong Architecture)
    unsigned int m_fbo[2];      // Dual Framebuffers
    unsigned int m_tex[2];      // Dual Textures (A and B)
    int m_activeIdx;            // Current target index (0 or 1)
    unsigned int m_depthRenderBuffer;
    
    // Shader programs
    unsigned int m_basicShader;
    unsigned int m_blendShader;
    
    // Vertex buffer for quad rendering
    unsigned int m_quadVAO;
    unsigned int m_quadVBO;
    
    // Framebuffer data cache
    mutable std::vector<uint8_t> m_framebufferData;
    mutable bool m_framebufferDirty;
    
    // OpenGL initialization
    void initializeOpenGL();
    void createFramebuffer();
    void createShaders();
    void createQuadMesh();
    
    // Cleanup
    void cleanup();
    
    // Shader utilities
    unsigned int compileShader(const char* source, unsigned int type);
    unsigned int linkProgram(unsigned int vertexShader, unsigned int fragmentShader);
};

} // namespace artflow
