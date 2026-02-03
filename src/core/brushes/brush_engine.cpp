/**
 * ArtFlow Studio - Brush Engine Implementation
 */

#include "brush_engine.h"
#include "../canvas/canvas.h"
#include "../layers/layer.h"
#include <cmath>
#include <algorithm>

namespace artflow {

BrushEngine::BrushEngine() {
    setRoundTip(0.8f);
}

BrushEngine::~BrushEngine() = default;

void BrushEngine::setSettings(const BrushSettings& settings) {
    m_settings = settings;
    if (m_tip.isRound) {
        setRoundTip(settings.hardness);
    }
}

void BrushEngine::setTip(const BrushTip& tip) {
    m_tip = tip;
}

void BrushEngine::setRoundTip(float hardness) {
    int diameter = static_cast<int>(m_settings.size * 2);
    if (diameter < 1) diameter = 1;
    generateRoundTip(diameter, hardness);
}

void BrushEngine::generateRoundTip(int diameter, float hardness) {
    m_tip.width = diameter;
    m_tip.height = diameter;
    m_tip.isRound = true;
    m_tip.mask.resize(diameter * diameter);
    
    float center = (diameter - 1) / 2.0f;
    float radius = diameter / 2.0f;
    
    for (int y = 0; y < diameter; ++y) {
        for (int x = 0; x < diameter; ++x) {
            float dx = x - center;
            float dy = y - center;
            float dist = std::sqrt(dx * dx + dy * dy) / radius;
            
            float value = 0.0f;
            if (dist <= 1.0f) {
                // Apply hardness falloff
                float edge = 1.0f - hardness;
                if (dist < hardness) {
                    value = 1.0f;
                } else {
                    float t = (dist - hardness) / edge;
                    value = 1.0f - t;
                }
            }
            
            m_tip.mask[y * diameter + x] = value;
        }
    }
}

void BrushEngine::beginStroke(Layer& layer, const Point& point) {
    m_isStroking = true;
    m_lastPoint = point;
    m_distanceAccum = 0.0f;
    
    float pressure = point.pressure;
    float size = m_settings.size;
    float opacity = m_settings.opacity;
    
    if (m_settings.pressureSize) {
        size *= m_settings.minSize + pressure * (1.0f - m_settings.minSize);
    }
    if (m_settings.pressureOpacity) {
        opacity *= m_settings.minOpacity + pressure * (1.0f - m_settings.minOpacity);
    }
    
    dabAt(layer, point.x, point.y, pressure, size, opacity);
}

void BrushEngine::continueStroke(Layer& layer, const Point& point) {
    if (!m_isStroking) return;
    interpolateDabs(layer, m_lastPoint, point);
    m_lastPoint = point;
}

void BrushEngine::endStroke(Layer& layer) {
    m_isStroking = false;
}

void BrushEngine::interpolateDabs(Layer& layer, const Point& from, const Point& to) {
    float dist = from.distanceTo(to);
    float spacing = m_settings.size * m_settings.spacing;
    if (spacing < 1.0f) spacing = 1.0f;
    
    float remaining = dist + m_distanceAccum;
    float t = (spacing - m_distanceAccum) / dist;
    
    while (t <= 1.0f && remaining >= spacing) {
        Point p = from.lerp(to, t);
        
        float size = m_settings.size;
        float opacity = m_settings.opacity;
        
        if (m_settings.pressureSize) {
            size *= m_settings.minSize + p.pressure * (1.0f - m_settings.minSize);
        }
        if (m_settings.pressureOpacity) {
            opacity *= m_settings.minOpacity + p.pressure * (1.0f - m_settings.minOpacity);
        }
        
        dabAt(layer, p.x, p.y, p.pressure, size, opacity);
        
        remaining -= spacing;
        t += spacing / dist;
    }
    
    m_distanceAccum = remaining;
}

void BrushEngine::dabAt(Layer& layer, float x, float y, float pressure, float size, float opacity) {
    if (m_tip.mask.empty()) return;
    
    float scale = size / m_settings.size;
    int dabSize = static_cast<int>(m_tip.width * scale);
    if (dabSize < 1) dabSize = 1;
    
    int startX = static_cast<int>(x - dabSize / 2.0f);
    int startY = static_cast<int>(y - dabSize / 2.0f);
    
    auto& data = const_cast<std::vector<uint8_t>&>(layer.getData());
    int layerWidth = layer.getWidth();
    int layerHeight = layer.getHeight();
    
    uint8_t brushR = static_cast<uint8_t>(m_settings.color.r * 255);
    uint8_t brushG = static_cast<uint8_t>(m_settings.color.g * 255);
    uint8_t brushB = static_cast<uint8_t>(m_settings.color.b * 255);
    
    for (int dy = 0; dy < dabSize; ++dy) {
        for (int dx = 0; dx < dabSize; ++dx) {
            int px = startX + dx;
            int py = startY + dy;
            
            if (px < 0 || px >= layerWidth || py < 0 || py >= layerHeight) continue;
            
            // Sample from tip mask with scaling
            float tipX = (dx / (float)dabSize) * m_tip.width;
            float tipY = (dy / (float)dabSize) * m_tip.height;
            int tx = std::clamp((int)tipX, 0, m_tip.width - 1);
            int ty = std::clamp((int)tipY, 0, m_tip.height - 1);
            
            float maskValue = m_tip.mask[ty * m_tip.width + tx];
            float alpha = maskValue * opacity * m_settings.flow;
            
            if (alpha < 0.001f) continue;
            
            size_t idx = (py * layerWidth + px) * 4;
            
            // Alpha blend
            float srcA = alpha;
            float dstA = data[idx + 3] / 255.0f;
            float outA = srcA + dstA * (1.0f - srcA);
            
            if (outA > 0.001f) {
                data[idx] = static_cast<uint8_t>((brushR * srcA + data[idx] * dstA * (1 - srcA)) / outA);
                data[idx + 1] = static_cast<uint8_t>((brushG * srcA + data[idx + 1] * dstA * (1 - srcA)) / outA);
                data[idx + 2] = static_cast<uint8_t>((brushB * srcA + data[idx + 2] * dstA * (1 - srcA)) / outA);
                data[idx + 3] = static_cast<uint8_t>(outA * 255);
            }
        }
    }
}

} // namespace artflow
