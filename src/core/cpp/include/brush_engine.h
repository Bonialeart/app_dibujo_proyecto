/**
 * ArtFlow Studio - Brush Engine
 * High-performance brush rendering engine
 */

#pragma once

#include <cstdint>
#include <vector>
#include <memory>
#include <string>

namespace artflow {

// Color representation (RGBA)
struct Color {
    uint8_t r, g, b, a;
    
    Color() : r(0), g(0), b(0), a(255) {}
    Color(uint8_t r, uint8_t g, uint8_t b, uint8_t a = 255) 
        : r(r), g(g), b(b), a(a) {}
    
    // Blend with another color
    Color blend(const Color& other, float opacity) const;
};

// Brush stroke point with pressure
struct StrokePoint {
    float x, y;
    float pressure;  // 0.0 - 1.0
    float tiltX, tiltY;  // Pen tilt
    uint64_t timestamp;
    
    StrokePoint() : x(0), y(0), pressure(1.0f), tiltX(0), tiltY(0), timestamp(0) {}
    StrokePoint(float x, float y, float pressure = 1.0f) 
        : x(x), y(y), pressure(pressure), tiltX(0), tiltY(0), timestamp(0) {}
};

// Brush settings
struct BrushSettings {
    float size = 10.0f;          // Base size in pixels
    float opacity = 1.0f;        // 0.0 - 1.0
    float hardness = 0.8f;       // Edge hardness 0.0 (soft) - 1.0 (hard)
    float flow = 1.0f;           // Paint flow rate
    float spacing = 0.1f;        // Stroke spacing (% of size)
    float grain = 0.0f;          // Texture grain (0.0 to 1.0)
    bool sizeByPressure = true;  // Size affected by pressure
    bool opacityByPressure = false;
    
    // Pro Features
    float jitter = 0.0f;          // Position jitter (0.0 to 1.0)
    float stabilization = 0.4f;   // Stroke smoothing (0.0 to 1.0)
    float rotation = 0.0f;        // Static rotation in degrees
    bool rotateWithStroke = false; // Dynamics: Rotate with direction
    
    // Texture support
    int textureId = -1;           // -1 = Solid, >=0 = Texture ID
    float textureScale = 1.0f;
    
    // Brush type
    enum class Type {
        Round,
        Pencil,
        Airbrush,
        Ink,
        Watercolor,
        Oil,
        Eraser,
        Custom
    } type = Type::Round;
};

// Forward declaration
class ImageBuffer;

/**
 * BrushEngine - Core brush rendering system
 */
class BrushEngine {
public:
    BrushEngine();
    ~BrushEngine();
    
    // Set current brush settings
    void setBrush(const BrushSettings& settings);
    const BrushSettings& getBrush() const { return m_brush; }
    
    // Set current color
    void setColor(const Color& color);
    const Color& getColor() const { return m_color; }
    
    // Stroke operations
    void beginStroke(const StrokePoint& point);
    void continueStroke(const StrokePoint& point);
    void endStroke();
    
    // Render a single dab at position
    void renderDab(ImageBuffer& target, float x, float y, float pressure);
    
    // Render stroke segment between two points
    void renderStrokeSegment(ImageBuffer& target, 
                              const StrokePoint& from, 
                              const StrokePoint& to);
    
    // Get interpolated stroke points for smooth rendering
    std::vector<StrokePoint> interpolatePoints(const StrokePoint& from, 
                                                 const StrokePoint& to) const;
    
private:
    BrushSettings m_brush;
    Color m_color;
    
    // Stroke state
    bool m_isStroking = false;
    StrokePoint m_lastPoint;
    float m_strokeDistance = 0.0f;
    
    // Internal rendering
    void applyBrushTexture(ImageBuffer& target, float x, float y, float size, float opacity);
    float calculateDabSize(float pressure) const;
    float calculateDabOpacity(float pressure) const;
};

} // namespace artflow
