/**
 * ArtFlow Studio - Renderer Implementation
 */

#define NOMINMAX
#include "renderer.h"
#include "../layers/layer.h"
#include "canvas.h"

#include <algorithm>
#include <stdexcept>
#include <cstring>

#include <stdexcept>
#include <cstring>

namespace artflow {

// Shader sources
const char* BASIC_VERTEX_SHADER = R"(
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec2 aTexCoord;

out vec2 TexCoord;

void main() {
    gl_Position = vec4(aPos, 0.0, 1.0);
    TexCoord = aTexCoord;
}
)";

const char* BASIC_FRAGMENT_SHADER = R"(
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;

uniform sampler2D layerTexture;
uniform float opacity;

void main() {
    vec4 texColor = texture(layerTexture, TexCoord);
    FragColor = vec4(texColor.rgb, texColor.a * opacity);
}
)";

const char* BLEND_FRAGMENT_SHADER = R"(
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;

uniform sampler2D baseTexture;
uniform sampler2D blendTexture;
uniform int blendMode;
uniform float opacity;

// Blend mode implementations
vec3 blendNormal(vec3 base, vec3 blend) {
    return blend;
}

vec3 blendMultiply(vec3 base, vec3 blend) {
    return base * blend;
}

vec3 blendScreen(vec3 base, vec3 blend) {
    return 1.0 - (1.0 - base) * (1.0 - blend);
}

vec3 blendOverlay(vec3 base, vec3 blend) {
    return mix(
        2.0 * base * blend,
        1.0 - 2.0 * (1.0 - base) * (1.0 - blend),
        step(0.5, base)
    );
}

vec3 blendSoftLight(vec3 base, vec3 blend) {
    return mix(
        2.0 * base * blend + base * base * (1.0 - 2.0 * blend),
        sqrt(base) * (2.0 * blend - 1.0) + 2.0 * base * (1.0 - blend),
        step(0.5, blend)
    );
}

vec3 blendHardLight(vec3 base, vec3 blend) {
    return blendOverlay(blend, base);
}

vec3 blendColorDodge(vec3 base, vec3 blend) {
    return min(base / (1.0 - blend + 0.001), vec3(1.0));
}

vec3 blendColorBurn(vec3 base, vec3 blend) {
    return 1.0 - min((1.0 - base) / (blend + 0.001), vec3(1.0));
}

vec3 blendDarken(vec3 base, vec3 blend) {
    return min(base, blend);
}

vec3 blendLighten(vec3 base, vec3 blend) {
    return max(base, blend);
}

vec3 blendDifference(vec3 base, vec3 blend) {
    return abs(base - blend);
}

void main() {
    vec4 baseColor = texture(baseTexture, TexCoord);
    vec4 blendColor = texture(blendTexture, TexCoord);
    
    vec3 result;
    
    if (blendMode == 0) result = blendNormal(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 1) result = blendMultiply(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 2) result = blendScreen(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 3) result = blendOverlay(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 4) result = blendSoftLight(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 5) result = blendHardLight(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 6) result = blendColorDodge(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 7) result = blendColorBurn(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 8) result = blendDarken(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 9) result = blendLighten(baseColor.rgb, blendColor.rgb);
    else if (blendMode == 10) result = blendDifference(baseColor.rgb, blendColor.rgb);
    else result = blendNormal(baseColor.rgb, blendColor.rgb);
    
    float alpha = blendColor.a * opacity;
    FragColor = vec4(mix(baseColor.rgb, result, alpha), max(baseColor.a, alpha));
}
const char* HSL_FRAGMENT_SHADER = R"(
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;
uniform sampler2D layerTexture;
uniform vec3 hslAdjust; // x=Hue, y=Saturation, z=Lightness

vec3 rgb2hsl(vec3 c) {
    float maxC = max(max(c.r, c.g), c.b);
    float minC = min(min(c.r, c.g), c.b);
    float delta = maxC - minC;
    vec3 hsl = vec3(0.0, 0.0, maxC);
    if (delta > 0.0001) {
        hsl.y = delta / (1.0 - abs(maxC + minC - 1.0));
        if (maxC == c.r) hsl.x = mod((c.g - c.b) / delta, 6.0);
        else if (maxC == c.g) hsl.x = (c.b - c.r) / delta + 2.0;
        else hsl.x = (c.r - c.g) / delta + 4.0;
        hsl.x /= 6.0;
    }
    return hsl;
}

vec3 hsl2rgb(vec3 c) {
    float k = mod(c.x * 6.0 + vec3(0, 4, 2), 6.0);
    float f = c.y * (1.0 - abs(2.0 * c.z - 1.0));
    return c.z - f * 0.5 * max(min(min(k - 3.0, 9.0 - k), 1.0), -1.0);
}

void main() {
    vec4 tex = texture(layerTexture, TexCoord);
    vec3 hsl = rgb2hsl(tex.rgb);
    hsl.x = mod(hsl.x + hslAdjust.x, 1.0);
    hsl.y = clamp(hsl.y + hslAdjust.y, 0.0, 1.0);
    hsl.z = clamp(hsl.z + hslAdjust.z, 0.0, 1.0);
    FragColor = vec4(hsl2rgb(hsl), tex.a);
}
)";

const char* BLOOM_FRAGMENT_SHADER = R"(
#version 330 core
in vec2 TexCoord;
out vec4 FragColor;
uniform sampler2D layerTexture;
uniform float threshold;
uniform float intensity;

void main() {
    vec4 tex = texture(layerTexture, TexCoord);
    float brightness = dot(tex.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 bloom = vec3(0.0);
    if (brightness > threshold) bloom = tex.rgb * intensity;
    FragColor = vec4(tex.rgb + bloom, tex.a);
}
)";

Renderer::Renderer(int width, int height)
    : m_width(width)
    , m_height(height)
    , m_activeIdx(0)
    , m_depthRenderBuffer(0)
    , m_basicShader(0)
    , m_blendShader(0)
    , m_quadVAO(0)
    , m_quadVBO(0)
    , m_framebufferDirty(true)
{
    initGLFunctions();
    m_fbo[0] = m_fbo[1] = 0;
    m_tex[0] = m_tex[1] = 0;
    m_framebufferData.resize(width * height * 4);
}

Renderer::~Renderer() {
    cleanup();
}

void Renderer::initializeOpenGL() {
    createFramebuffer();
    createShaders();
    createQuadMesh();
}

void Renderer::createFramebuffer() {
    // Ping-Pong Architecture: 2 Framebuffers, 2 Textures
    glGenFramebuffers(2, m_fbo);
    glGenTextures(2, m_tex);

    for (int i = 0; i < 2; ++i) {
        glBindFramebuffer(GL_FRAMEBUFFER, m_fbo[i]);
        glBindTexture(GL_TEXTURE_2D, m_tex[i]);
        
        // Use high-precision format if possible for watercolor
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, m_width, m_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, m_tex[i], 0);
    }
    
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
}

void Renderer::createShaders() {
    // Compile and link shader programs
    // m_basicShader = linkProgram(
    //     compileShader(BASIC_VERTEX_SHADER, GL_VERTEX_SHADER),
    //     compileShader(BASIC_FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
    // );
    
    // m_blendShader = linkProgram(
    //     compileShader(BASIC_VERTEX_SHADER, GL_VERTEX_SHADER),
    //     compileShader(BLEND_FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
    // );
}

void Renderer::createQuadMesh() {
    // Create fullscreen quad for rendering textures
    float quadVertices[] = {
        // positions   // texCoords
        -1.0f,  1.0f,  0.0f, 1.0f,
        -1.0f, -1.0f,  0.0f, 0.0f,
         1.0f, -1.0f,  1.0f, 0.0f,
        
        -1.0f,  1.0f,  0.0f, 1.0f,
         1.0f, -1.0f,  1.0f, 0.0f,
         1.0f,  1.0f,  1.0f, 1.0f
    };
    
    // glGenVertexArrays(1, &m_quadVAO);
    // glGenBuffers(1, &m_quadVBO);
    // glBindVertexArray(m_quadVAO);
    // glBindBuffer(GL_ARRAY_BUFFER, m_quadVBO);
    // glBufferData(GL_ARRAY_BUFFER, sizeof(quadVertices), quadVertices, GL_STATIC_DRAW);
    // glEnableVertexAttribArray(0);
    // glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
    // glEnableVertexAttribArray(1);
    // glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)(2 * sizeof(float)));
}

void Renderer::cleanup() {
    if (m_fbo[0]) glDeleteFramebuffers(2, m_fbo);
    if (m_tex[0]) glDeleteTextures(2, m_tex);
    if (m_depthRenderBuffer) glDeleteRenderbuffers(1, &m_depthRenderBuffer);
    
    if (m_basicShader) glDeleteProgram(m_basicShader);
    if (m_blendShader) glDeleteProgram(m_blendShader);
    if (m_quadVAO) glDeleteVertexArrays(1, &m_quadVAO);
    if (m_quadVBO) glDeleteBuffers(1, &m_quadVBO);
    
    m_fbo[0] = m_fbo[1] = 0;
    m_tex[0] = m_tex[1] = 0;
}

void Renderer::beginFrame() {
    // Target the current ping-pong FBO
    glBindFramebuffer(GL_FRAMEBUFFER, m_fbo[m_activeIdx]);
    glViewport(0, 0, m_width, m_height);
    
    m_framebufferDirty = true;
}

void Renderer::endFrame() {
    // glBindFramebuffer(GL_FRAMEBUFFER, 0);
}

void Renderer::drawBackground(const Color& color) {
    // glClearColor(color.r, color.g, color.b, color.a);
    // glClear(GL_COLOR_BUFFER_BIT);
    
    // For software rendering fallback
    for (int i = 0; i < m_width * m_height; ++i) {
        m_framebufferData[i * 4 + 0] = static_cast<uint8_t>(color.r * 255);
        m_framebufferData[i * 4 + 1] = static_cast<uint8_t>(color.g * 255);
        m_framebufferData[i * 4 + 2] = static_cast<uint8_t>(color.b * 255);
        m_framebufferData[i * 4 + 3] = static_cast<uint8_t>(color.a * 255);
    }
}

void Renderer::drawLayer(const Layer& layer) {
    if (!layer.isVisible()) return;
    
    drawLayerWithBlendMode(layer, 0); // Normal blend
}

void Renderer::drawLayerWithBlendMode(const Layer& layer, int blendMode) {
    // In a real implementation:
    // 1. Upload layer data to texture
    // 2. Use blend shader with appropriate blend mode
    // 3. Render quad to framebuffer
    
    // For now, we'll do simple alpha compositing in software
    const auto& layerData = layer.getData();
    float opacity = layer.getOpacity();
    
    for (int y = 0; y < m_height; ++y) {
        for (int x = 0; x < m_width; ++x) {
            int i = (y * m_width + x) * 4;
            
            if (i + 3 >= static_cast<int>(layerData.size())) continue;
            
            float srcA = (layerData[i + 3] / 255.0f) * opacity;
            if (srcA < 0.001f) continue;
            
            float srcR = layerData[i + 0] / 255.0f;
            float srcG = layerData[i + 1] / 255.0f;
            float srcB = layerData[i + 2] / 255.0f;
            
            float dstR = m_framebufferData[i + 0] / 255.0f;
            float dstG = m_framebufferData[i + 1] / 255.0f;
            float dstB = m_framebufferData[i + 2] / 255.0f;
            float dstA = m_framebufferData[i + 3] / 255.0f;
            
            float outA = srcA + dstA * (1.0f - srcA);
            float outR = (srcR * srcA + dstR * dstA * (1.0f - srcA)) / (outA + 0.001f);
            float outG = (srcG * srcA + dstG * dstA * (1.0f - srcA)) / (outA + 0.001f);
            float outB = (srcB * srcA + dstB * dstA * (1.0f - srcA)) / (outA + 0.001f);
            
            m_framebufferData[i + 0] = static_cast<uint8_t>(outR * 255);
            m_framebufferData[i + 1] = static_cast<uint8_t>(outG * 255);
            m_framebufferData[i + 2] = static_cast<uint8_t>(outB * 255);
            m_framebufferData[i + 3] = static_cast<uint8_t>(outA * 255);
        }
    }
}

const uint8_t* Renderer::getFramebufferData() const {
    return m_framebufferData.data();
}

void Renderer::getFramebufferData(uint8_t* buffer, size_t bufferSize) const {
    size_t copySize = (std::min)(bufferSize, m_framebufferData.size());
    std::memcpy(buffer, m_framebufferData.data(), copySize);
}

void Renderer::setBufferData(const uint8_t* buffer) {
    if (!m_tex[0] || !buffer) return;
    
    // Upload to both textures to keep Ping-Pong state consistent
    for (int i = 0; i < 2; ++i) {
        glBindTexture(GL_TEXTURE_2D, m_tex[i]);
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, m_width, m_height, GL_RGBA, GL_UNSIGNED_BYTE, buffer);
    }
    glBindTexture(GL_TEXTURE_2D, 0);
}

void Renderer::resize(int width, int height) {
    if (width == m_width && height == m_height) return;
    
    m_width = width;
    m_height = height;
    m_framebufferData.resize(width * height * 4);
    
    // Recreate OpenGL resources
    cleanup();
    initializeOpenGL();
}

unsigned int Renderer::compileShader(const char* source, unsigned int type) {
    // unsigned int shader = glCreateShader(type);
    // glShaderSource(shader, 1, &source, nullptr);
    // glCompileShader(shader);
    // return shader;
    return 0;
}

unsigned int Renderer::linkProgram(unsigned int vertexShader, unsigned int fragmentShader) {
    // unsigned int program = glCreateProgram();
    // glAttachShader(program, vertexShader);
    // glAttachShader(program, fragmentShader);
    // glLinkProgram(program);
    // glDeleteShader(vertexShader);
    // glDeleteShader(fragmentShader);
    // return program;
    return 0;
}

} // namespace artflow
