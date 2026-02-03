/**
 * ArtFlow Studio - Layer Implementation
 */

#include "layer.h"
#include "../canvas/canvas.h"
#include <algorithm>
#include <cstring>

namespace artflow {

Layer::Layer(int width, int height, const std::string& name)
    : m_name(name), m_width(width), m_height(height)
{
    m_data.resize(width * height * 4, 0);
}

Layer::~Layer() = default;

Layer::Layer(Layer&& other) noexcept = default;
Layer& Layer::operator=(Layer&& other) noexcept = default;

void Layer::setOpacity(float opacity) {
    m_opacity = std::clamp(opacity, 0.0f, 1.0f);
}

void Layer::resize(int width, int height) {
    std::vector<uint8_t> newData(width * height * 4, 0);
    
    int copyWidth = std::min(width, m_width);
    int copyHeight = std::min(height, m_height);
    
    for (int y = 0; y < copyHeight; ++y) {
        for (int x = 0; x < copyWidth; ++x) {
            size_t srcIdx = (y * m_width + x) * 4;
            size_t dstIdx = (y * width + x) * 4;
            std::memcpy(&newData[dstIdx], &m_data[srcIdx], 4);
        }
    }
    
    m_width = width;
    m_height = height;
    m_data = std::move(newData);
}

void Layer::setData(const std::vector<uint8_t>& data) {
    if (data.size() == m_data.size()) {
        m_data = data;
    }
}

void Layer::clear() {
    std::fill(m_data.begin(), m_data.end(), 0);
}

void Layer::fill(const Color& color) {
    for (size_t i = 0; i < m_data.size(); i += 4) {
        m_data[i + 0] = static_cast<uint8_t>(color.r * 255);
        m_data[i + 1] = static_cast<uint8_t>(color.g * 255);
        m_data[i + 2] = static_cast<uint8_t>(color.b * 255);
        m_data[i + 3] = static_cast<uint8_t>(color.a * 255);
    }
}

void Layer::copyFrom(const Layer& other) {
    if (other.m_width == m_width && other.m_height == m_height) {
        m_data = other.m_data;
        m_opacity = other.m_opacity;
        m_blendMode = other.m_blendMode;
    }
}

void Layer::mergeWith(const Layer& other) {
    if (!other.m_visible || other.m_width != m_width || other.m_height != m_height) return;
    
    for (int i = 0; i < m_width * m_height; ++i) {
        size_t idx = i * 4;
        float srcA = (other.m_data[idx + 3] / 255.0f) * other.m_opacity;
        if (srcA < 0.001f) continue;
        
        float srcR = other.m_data[idx] / 255.0f;
        float srcG = other.m_data[idx + 1] / 255.0f;
        float srcB = other.m_data[idx + 2] / 255.0f;
        
        float dstR = m_data[idx] / 255.0f;
        float dstG = m_data[idx + 1] / 255.0f;
        float dstB = m_data[idx + 2] / 255.0f;
        float dstA = m_data[idx + 3] / 255.0f;
        
        float outA = srcA + dstA * (1.0f - srcA);
        m_data[idx] = static_cast<uint8_t>(((srcR * srcA + dstR * dstA * (1 - srcA)) / outA) * 255);
        m_data[idx + 1] = static_cast<uint8_t>(((srcG * srcA + dstG * dstA * (1 - srcA)) / outA) * 255);
        m_data[idx + 2] = static_cast<uint8_t>(((srcB * srcA + dstB * dstA * (1 - srcA)) / outA) * 255);
        m_data[idx + 3] = static_cast<uint8_t>(outA * 255);
    }
}

} // namespace artflow
