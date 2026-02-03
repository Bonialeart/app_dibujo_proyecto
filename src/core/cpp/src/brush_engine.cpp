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
    if (m_brush.sizeByPressure) {
        return m_brush.size * (0.3f + 0.7f * pressure);
    }
    return m_brush.size;
}

float BrushEngine::calculateDabOpacity(float pressure) const {
    float opacity = m_brush.opacity * m_brush.flow;
    if (m_brush.opacityByPressure) {
        opacity *= pressure;
    }
    return std::clamp(opacity, 0.0f, 1.0f);
}

void BrushEngine::renderDab(ImageBuffer& target, float x, float y, float pressure) {
    float size = calculateDabSize(pressure);
    float opacity = calculateDabOpacity(pressure);
    
    // Apply Position Jitter
    if (m_brush.jitter > 0.01f) {
        float offset = size * m_brush.jitter;
        x += (static_cast<float>(rand()) / RAND_MAX * 2.0f - 1.0f) * offset;
        y += (static_cast<float>(rand()) / RAND_MAX * 2.0f - 1.0f) * offset;
    }
    
    // Choose rendering mode
    if (m_brush.type == BrushSettings::Type::Eraser) {
        // Eraser logic (simple for now, target buffer might need transparency support)
        target.drawCircle(
            static_cast<int>(x), static_cast<int>(y), size / 2.0f,
            0, 0, 0, 0, // Transparent black
            m_brush.hardness
        );
    } else {
        // Standard Brush logic
        target.drawCircle(
            static_cast<int>(x), static_cast<int>(y), size / 2.0f,
            m_color.r, m_color.g, m_color.b, 
            static_cast<uint8_t>(opacity * 255),
            m_brush.hardness,
            m_brush.grain
        );
    }
}

std::vector<StrokePoint> BrushEngine::interpolatePoints(const StrokePoint& from, 
                                                          const StrokePoint& to) const {
    std::vector<StrokePoint> points;
    
    // Simple Stabilization (Exponential Smoothing)
    StrokePoint stableTo = to;
    if (m_brush.stabilization > 0.01f) {
        float factor = 1.0f - m_brush.stabilization;
        stableTo.x = from.x + (to.x - from.x) * factor;
        stableTo.y = from.y + (to.y - from.y) * factor;
    }

    float dx = stableTo.x - from.x;
    float dy = stableTo.y - from.y;
    float distance = std::sqrt(dx * dx + dy * dy);
    
    // Spacing based on brush size
    float spacing = std::max(1.0f, m_brush.size * m_brush.spacing);
    int steps = static_cast<int>(distance / spacing);
    
    if (steps < 1) steps = 1;
    
    for (int i = 1; i <= steps; ++i) { // i=1 to avoid double drawing 'from' point
        float t = static_cast<float>(i) / steps;
        StrokePoint p;
        p.x = from.x + dx * t;
        p.y = from.y + dy * t;
        p.pressure = from.pressure + (to.pressure - from.pressure) * t;
        p.tiltX = from.tiltX + (to.tiltX - from.tiltX) * t;
        p.tiltY = from.tiltY + (to.tiltY - from.tiltY) * t;
        points.push_back(p);
    }
    
    return points;
}

void BrushEngine::renderStrokeSegment(ImageBuffer& target, 
                                       const StrokePoint& from, 
                                       const StrokePoint& to) {
    auto points = interpolatePoints(from, to);
    
    for (const auto& p : points) {
        renderDab(target, p.x, p.y, p.pressure);
    }
}

} // namespace artflow
