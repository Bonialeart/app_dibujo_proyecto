#include "stroke_renderer.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <cmath>
#include <cstring> 

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace artflow {

StrokeRenderer::StrokeRenderer() 
    : m_program(0), m_vao(0), m_vbo(0)
    , m_brushTexture(0), m_paperTexture(0)
    , m_uMVP(-1), m_uCanvasSize(-1)
    , m_uPos(-1), m_uSize(-1), m_uRotation(-1)
    , m_uColor(-1), m_uHardness(-1), m_uMode(-1)
    , m_uPaperTex(-1), m_uCanvasTex(-1), m_uWetMap(-1)
    , m_isInitialized(false)
{
    // Initialize projection matrix to identity
    std::memset(m_proj, 0, 16 * sizeof(float));
    m_proj[0] = 1.0f; m_proj[5] = 1.0f; m_proj[10] = 1.0f; m_proj[15] = 1.0f;
}

StrokeRenderer::~StrokeRenderer() {
    if (m_isInitialized) {
        if(m_vbo) glDeleteBuffers(1, &m_vbo);
        if(m_vao) glDeleteVertexArrays(1, &m_vao);
        if(m_program) glDeleteProgram(m_program);
        if(m_brushTexture) { GLuint t = m_brushTexture; glDeleteTextures(1, &t); }
        if(m_paperTexture) { GLuint t = m_paperTexture; glDeleteTextures(1, &t); }
    }
}

// Helper to load file
std::string loadFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    std::stringstream buffer;
    buffer << f.rdbuf();
    return buffer.str();
}

GLuint compileShader(GLenum type, const char* source) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    
    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char infoLog[512];
        glGetShaderInfoLog(shader, 512, nullptr, infoLog);
        std::cerr << "Shader compile error: " << infoLog << std::endl;
        return 0;
    }
    return shader;
}

bool StrokeRenderer::initialize() {
    if(!initGLFunctions()) {
        std::cerr << "Failed to init GL functions" << std::endl;
        return false;
    }

    // Load Shaders
    // Try current dir or absolute path
    std::string vertSrc = loadFile("src/core/shaders/brush.vert");
    if(vertSrc.empty()) vertSrc = loadFile("e:/app_dibujo_proyecto/src/core/shaders/brush.vert");

    std::string fragSrc = loadFile("src/core/shaders/brush.frag");
    if(fragSrc.empty()) fragSrc = loadFile("e:/app_dibujo_proyecto/src/core/shaders/brush.frag");

    if(vertSrc.empty() || fragSrc.empty()) {
        std::cerr << "Failed to load shaders" << std::endl;
        return false;
    }

    GLuint vert = compileShader(GL_VERTEX_SHADER, vertSrc.c_str());
    GLuint frag = compileShader(GL_FRAGMENT_SHADER, fragSrc.c_str());

    if(!vert || !frag) return false;

    m_program = glCreateProgram();
    glAttachShader(m_program, vert);
    glAttachShader(m_program, frag);
    glLinkProgram(m_program);

    GLint success;
    glGetProgramiv(m_program, GL_LINK_STATUS, &success);
    if(!success) {
         char infoLog[512];
        glGetProgramInfoLog(m_program, 512, nullptr, infoLog);
        std::cerr << "Program link error: " << infoLog << std::endl;
        return false;
    }

    glDeleteShader(vert);
    glDeleteShader(frag);

    // Cache Uniforms
    m_uMVP = glGetUniformLocation(m_program, "uMVP");
    m_uCanvasSize = glGetUniformLocation(m_program, "uCanvasSize");
    m_uPos = glGetUniformLocation(m_program, "uPos");
    m_uSize = glGetUniformLocation(m_program, "uSize");
    m_uRotation = glGetUniformLocation(m_program, "uRotation");
    m_uColor = glGetUniformLocation(m_program, "uColor");
    m_uHardness = glGetUniformLocation(m_program, "uHardness");
    m_uMode = glGetUniformLocation(m_program, "uMode");
    m_uPressure = glGetUniformLocation(m_program, "uPressure");
    m_uCanvasTex = glGetUniformLocation(m_program, "uCanvasTex");
    m_uWetMap = glGetUniformLocation(m_program, "uWetMap");
    m_uPaperTex = glGetUniformLocation(m_program, "uPaperTex");

    createQuad();

    m_isInitialized = true;
    return true;
}

void StrokeRenderer::createQuad() {
    float vertices[] = {
        // Pos      // Tex
        -0.5f, -0.5f, 0.0f, 0.0f,
         0.5f, -0.5f, 1.0f, 0.0f,
        -0.5f,  0.5f, 0.0f, 1.0f,
        
        -0.5f,  0.5f, 0.0f, 1.0f,
         0.5f, -0.5f, 1.0f, 0.0f,
         0.5f,  0.5f, 1.0f, 1.0f
    };

    glGenVertexArrays(1, &m_vao);
    glGenBuffers(1, &m_vbo);

    glBindVertexArray(m_vao);

    glBindBuffer(GL_ARRAY_BUFFER, m_vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

    // Pos
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
    
    // UV
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)(2 * sizeof(float)));

    glBindVertexArray(0);
}

void StrokeRenderer::setBrushTip(const unsigned char* data, int width, int height) {
    if (m_brushTexture == 0) glGenTextures(1, &m_brushTexture);
    
    glBindTexture(GL_TEXTURE_2D, m_brushTexture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);
}

void StrokeRenderer::setPaperTexture(const unsigned char* data, int width, int height) {
    if (m_paperTexture == 0) glGenTextures(1, &m_paperTexture);
    
    glBindTexture(GL_TEXTURE_2D, m_paperTexture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    // Wrap repeat is useful for paper patterns
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, 0x2901); // GL_REPEAT
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, 0x2901);
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data);
}

void StrokeRenderer::beginFrame(int width, int height) {
    if (!m_isInitialized) return;

    glDisable(GL_BLEND);
    glDisable(GL_DEPTH_TEST);
    glViewport(0, 0, width, height);
    
    float L=0, R=(float)width, B=(float)height, T=0;
    
    std::memset(m_proj, 0, 16*sizeof(float));
    m_proj[0] = 2.0f / (R - L);
    m_proj[5] = 2.0f / (T - B);
    m_proj[10] = -1.0f;
    m_proj[15] = 1.0f;
    m_proj[12] = -(R + L) / (R - L);
    m_proj[13] = -(T + B) / (T - B);

    glUseProgram(m_program);
    glUniformMatrix4fv(m_uMVP, 1, GL_FALSE, m_proj);
    
    // Update global canvas size for shader normalization
    if (m_uCanvasSize >= 0) {
        glUniform2f(m_uCanvasSize, (float)width, (float)height);
    }
}

void StrokeRenderer::endFrame() {
    glUseProgram(0);
}

void StrokeRenderer::drawDab(float x, float y, float size, float rotation, 
                             float r, float g, float b, float a, float hardness, float pressure, int mode) {
    drawDabPingPong(x, y, size, rotation, r, g, b, a, hardness, pressure, mode, 0, 0);
}

void StrokeRenderer::drawDabPingPong(float x, float y, float size, float rotation, 
                                     float r, float g, float b, float a, float hardness, float pressure, int mode,
                                     unsigned int canvasTextureId, unsigned int wetMapTextureId) {
    if (!m_isInitialized) return;

    glUniform2f(m_uPos, x, y);
    glUniform1f(m_uSize, size);
    glUniform1f(m_uRotation, rotation);
    glUniform4f(m_uColor, r, g, b, a);
    glUniform1f(m_uHardness, hardness);
    glUniform1f(m_uPressure, pressure);
    glUniform1i(m_uMode, mode);

    // Bind Brush Texture to Unit 0
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, m_brushTexture);
    // (Shader should default uTex to 0)

    // Bind Paper Texture to Unit 1
    if (m_uPaperTex >= 0) {
        glActiveTexture(GL_TEXTURE0 + 1);
        glBindTexture(GL_TEXTURE_2D, m_paperTexture);
        glUniform1i(m_uPaperTex, 1);
    }

    // Ping-Pong Source (Previous Canvas)
    if (m_uCanvasTex >= 0 && canvasTextureId != 0) {
        glActiveTexture(GL_TEXTURE0 + 2);
        glBindTexture(GL_TEXTURE_2D, canvasTextureId);
        glUniform1i(m_uCanvasTex, 2);
    }

    // Wet Map
    if (m_uWetMap >= 0 && wetMapTextureId != 0) {
        glActiveTexture(GL_TEXTURE0 + 3);
        glBindTexture(GL_TEXTURE_2D, wetMapTextureId);
        glUniform1i(m_uWetMap, 3);
    }

    glBindVertexArray(m_vao);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glBindVertexArray(0);
}

} // namespace artflow
