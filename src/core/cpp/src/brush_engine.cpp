/**
 * ArtFlow Studio - Brush Engine Implementation
 */

#include "brush_engine.h"
#include "image_buffer.h"
#include <cmath>
#include <algorithm>

namespace artflow {

// Color blend implementation
Color Color::blend(const Color& other, float opacity) const {
    float a = opacity * (other.a / 255.0f);
    float invA = 1.0f - a;
    
    return Color(
        static_cast<uint8_t>(std::clamp(r * invA + other.r * a, 0.0f, 255.0f)),
        static_cast<uint8_t>(std::clamp(g * invA + other.g * a, 0.0f, 255.0f)),
        static_cast<uint8_t>(std::clamp(b * invA + other.b * a, 0.0f, 255.0f)),
        static_cast<uint8_t>(std::clamp(this->a + other.a * opacity, 0.0f, 255.0f))
    );
}

BrushEngine::BrushEngine() 
    : m_color(0, 0, 0, 255) {
}

BrushEngine::~BrushEngine() = default;

void BrushEngine::setBrush(const BrushSettings& settings) {
    m_brush = settings;
}

void BrushEngine::setColor(const Color& color) {
    m_color = color;
}

void BrushEngine::beginStroke(const StrokePoint& point) {
    m_isStroking = true;
    m_lastPoint = point;
    m_strokeDistance = 0.0f;
}

void BrushEngine::continueStroke(const StrokePoint& point) {
    if (!m_isStroking) return;
    m_lastPoint = point;
}

void BrushEngine::endStroke() {
    m_isStroking = false;
    m_strokeDistance = 0.0f;
}

float BrushEngine::calculateDabSize(float pressure) const {
    float baseSize = m_brush.size;
    
    // Pressure dynamics
    if (m_brush.sizeByPressure) {
        baseSize *= (0.2f + 0.8f * pressure);
    }
    
    // Velocity dynamics (Simulated - in a real engine we'd compute delta time)
    // For now we'll assume pressure might drop slightly when fast or use a stored velocity if we tracked it.
    // Let's add a simple placeholder for velocity-based size in the caller or interpolate.
    
    return baseSize;
}

float BrushEngine::calculateDabOpacity(float pressure) const {
    float opacity = m_brush.opacity * m_brush.flow;
    if (m_brush.opacityByPressure) {
        opacity *= (0.1f + 0.9f * pressure);
    }
    return std::clamp(opacity, 0.0f, 1.0f);
}

void BrushEngine::renderDab(ImageBuffer& target, float x, float y, float pressure, bool alphaLock, const ImageBuffer* mask) {
    float size = calculateDabSize(pressure);
    float opacity = calculateDabOpacity(pressure);
    
    // 1. POSITION JITTER
    if (m_brush.jitter > 0.001f) {
        float offset = size * m_brush.jitter * 2.0f;
        x += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * offset;
        y += (static_cast<float>(rand()) / RAND_MAX - 0.5f) * offset;
    }
    
    // 2. ERASER MODE
    if (m_brush.type == BrushSettings::Type::Eraser) {
        target.drawCircle(static_cast<int>(x), static_cast<int>(y), size / 2.0f,
                         0, 0, 0, 0, m_brush.hardness, 0.0f, alphaLock, mask);
        return;
    }

    // 3. COLOR MIXING ENGINE (Kubelka-Munk / RMS Simplified for C++)
    // We sample the destination color to "dirty" the brush (Color Pickup)
    uint8_t* dst = target.pixelAt(static_cast<int>(x), static_cast<int>(y));
    Color finalColor = m_color;
    
    if (dst && dst[3] > 0 && (m_brush.type == BrushSettings::Type::Watercolor || m_brush.type == BrushSettings::Type::Oil)) {
        // Simple Pickup Mix: 20% canvas color, 80% brush color
        float pickup = 0.2f;
        finalColor.r = static_cast<uint8_t>(m_color.r * 0.8f + dst[0] * pickup);
        finalColor.g = static_cast<uint8_t>(m_color.g * 0.8f + dst[1] * pickup);
        finalColor.b = static_cast<uint8_t>(m_color.b * 0.8f + dst[2] * pickup);
    }

    // 4. RENDER MODES
    if (m_brush.tipImage) {
        // Note: For stamps, we'd need to add mask support to composite() too.
        // For now, only circle dabs support clipping in this version.
        target.composite(*m_brush.tipImage, 
                        static_cast<int>(x - m_brush.tipImage->width()/2), 
                        static_cast<int>(y - m_brush.tipImage->height()/2), 
                        opacity);
    }
    else {
        // Professional Shader-like Dab with grain and hardness
        target.drawCircle(
            static_cast<int>(x), static_cast<int>(y), size / 2.0f,
            finalColor.r, finalColor.g, finalColor.b, 
            static_cast<uint8_t>(opacity * 255),
            m_brush.hardness,
            m_brush.grain,
            alphaLock,
            mask
        );
    }
}

std::vector<StrokePoint> BrushEngine::interpolatePoints(const StrokePoint& from, 
                                                          const StrokePoint& to) const {
    std::vector<StrokePoint> points;
    
    // 1. ADVANCED STABILIZATION
    StrokePoint pTo = to;
    
    // Exponential Smoothing (Stabilization)
    if (m_brush.stabilization > 0.01f) {
        float s = 1.0f - m_brush.stabilization;
        pTo.x = from.x + (to.x - from.x) * s;
        pTo.y = from.y + (to.y - from.y) * s;
    }
    
    // Streamline (Path correction - pulling the string)
    if (m_brush.streamline > 0.01f) {
        // Simplified streamline: blend direction with previous movement
        // (In a full engine we'd use a Catmull-Rom spline)
    }

    float dx = pTo.x - from.x;
    float dy = pTo.y - from.y;
    float distance = std::sqrt(dx * dx + dy * dy);
    
    // Spacing based on brush size - Use a tighter default for C++ engine smoothness
    float spacingRatio = std::max(0.01f, m_brush.spacing); 
    float spacing = std::max(0.25f, (m_brush.size * spacingRatio) * 0.5f); // Half the spacing for C++ smoothness
    int steps = static_cast<int>(distance / spacing);
    
    if (steps < 1) {
        // If distance is too small but we moved, at least one point if far enough
        if (distance > 0.1f) steps = 1;
        else return points;
    }
    
    for (int i = 1; i <= steps; ++i) {
        float t = static_cast<float>(i) / steps;
        StrokePoint p;
        p.x = from.x + dx * t;
        p.y = from.y + dy * t;
        p.pressure = from.pressure + (to.pressure - from.pressure) * t;
        
        // Velocity detection (Distance between interpolated points)
        // Can be used to drive size/opacity if velocityDynamics is set
        
        points.push_back(p);
    }
    
    return points;
}

void BrushEngine::renderStrokeSegment(ImageBuffer& target, 
                                       const StrokePoint& from, 
                                       const StrokePoint& to,
                                       bool alphaLock, const ImageBuffer* mask) {
    auto points = interpolatePoints(from, to);
    for (const auto& p : points) {
        renderDab(target, p.x, p.y, p.pressure, alphaLock, mask);
    }
}

} // namespace artflow
