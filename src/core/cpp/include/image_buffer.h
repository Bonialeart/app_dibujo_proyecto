/**
 * ArtFlow Studio - Image Buffer
 * High-performance pixel buffer for rendering
 */

#pragma once

#include <cstdint>
#include <vector>
#include <memory>

namespace artflow {

/**
 * ImageBuffer - RGBA pixel buffer for layer/canvas data
 */
class ImageBuffer {
public:
    ImageBuffer(int width, int height);
    ~ImageBuffer();
    
    // Dimensions
    int width() const { return m_width; }
    int height() const { return m_height; }
    
    // Pixel access
    uint8_t* data() { return m_data.data(); }
    const uint8_t* data() const { return m_data.data(); }
    
    // Get pixel at position (returns nullptr if out of bounds)
    uint8_t* pixelAt(int x, int y);
    const uint8_t* pixelAt(int x, int y) const;
    
    // Set pixel color
    void setPixel(int x, int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255);
    
    // Fill entire buffer
    void fill(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255);
    void clear();
    
    // Blend a color onto pixel with alpha blending. Optional alphaLock restricts
    // painting to areas that already have some alpha.
    void blendPixel(int x, int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a, bool alphaLock = false, bool isEraser = false);
    
    // Draw a filled circle (for brush dabs)
    void drawCircle(int cx, int cy, float radius, 
                    uint8_t r, uint8_t g, uint8_t b, uint8_t a,
                    float hardness = 1.0f, float grain = 0.0f, 
                    bool alphaLock = false, bool isEraser = false, const ImageBuffer* mask = nullptr);
    
    // Copy from another buffer
    void copyFrom(const ImageBuffer& other);
    
    // Composite another buffer on top
    void composite(const ImageBuffer& other, int offsetX = 0, int offsetY = 0, float opacity = 1.0f);
    
    // Get raw bytes for Python/QML interop
    std::vector<uint8_t> getBytes() const;
    
    // Draw a textured stroke (High Performance C++ Splatting)
    // Moves the heavy loop from Python to C++ for lag-free painting
    void drawStrokeTextured(float x1, float y1, float x2, float y2, 
                           const ImageBuffer& stamp, 
                           float spacing, float opacity, 
                           bool rotate, float angle_jitter,
                           bool is_watercolor,
                           const ImageBuffer* paper_texture = nullptr);
                           
    // Create from raw bytes
    static std::unique_ptr<ImageBuffer> fromBytes(const std::vector<uint8_t>& bytes, int width, int height);

private:
    int m_width;
    int m_height;
    std::vector<uint8_t> m_data;  // RGBA format (4 bytes per pixel)
    
    size_t pixelIndex(int x, int y) const {
        return static_cast<size_t>((y * m_width + x) * 4);
    }
    
    bool isValidCoord(int x, int y) const {
        return x >= 0 && x < m_width && y >= 0 && y < m_height;
    }
};

} // namespace artflow
