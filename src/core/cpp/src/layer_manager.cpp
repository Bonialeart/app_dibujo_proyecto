/**
 * ArtFlow Studio - Layer Manager Implementation
 */

#include "layer_manager.h"
#include <algorithm>

namespace artflow {

Layer::Layer(const std::string& name, int width, int height, Type type)
    : name(name)
    , buffer(std::make_unique<ImageBuffer>(width, height))
    , wetnessMap(std::make_unique<ImageBuffer>(width, height))
    , pigmentMap(std::make_unique<ImageBuffer>(width, height)) 
    , type(type)
{
}

LayerManager::LayerManager(int width, int height)
    : m_width(width), m_height(height) {
    // Create default background layer
    addLayer("Background", Layer::Type::Background);
    m_layers[0]->buffer->fill(255, 255, 255, 255); // Default white
}

LayerManager::~LayerManager() = default;

int LayerManager::addLayer(const std::string& name, Layer::Type type) {
    auto layer = std::make_unique<Layer>(name, m_width, m_height, type);
    m_layers.push_back(std::move(layer));
    m_activeIndex = static_cast<int>(m_layers.size()) - 1;
    return m_activeIndex;
}

void LayerManager::removeLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return;
    if (m_layers.size() <= 1) return;  // Keep at least one layer
    
    m_layers.erase(m_layers.begin() + index);
    m_activeIndex = std::clamp(m_activeIndex, 0, static_cast<int>(m_layers.size()) - 1);
}

void LayerManager::moveLayer(int fromIndex, int toIndex) {
    if (fromIndex < 0 || fromIndex >= static_cast<int>(m_layers.size())) return;
    if (toIndex < 0 || toIndex >= static_cast<int>(m_layers.size())) return;
    
    auto layer = std::move(m_layers[fromIndex]);
    m_layers.erase(m_layers.begin() + fromIndex);
    m_layers.insert(m_layers.begin() + toIndex, std::move(layer));
}

void LayerManager::duplicateLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return;
    
    const Layer* src = m_layers[index].get();
    auto newLayer = std::make_unique<Layer>(src->name + " Copy", m_width, m_height);
    newLayer->buffer->copyFrom(*src->buffer);
    newLayer->wetnessMap->copyFrom(*src->wetnessMap);
    newLayer->pigmentMap->copyFrom(*src->pigmentMap);
    newLayer->opacity = src->opacity;
    newLayer->blendMode = src->blendMode;
    newLayer->visible = src->visible;
    newLayer->alphaLock = src->alphaLock;
    newLayer->clipped = src->clipped;
    newLayer->type = src->type;
    
    m_layers.insert(m_layers.begin() + index + 1, std::move(newLayer));
}

void LayerManager::mergeDown(int index) {
    if (index <= 0 || index >= static_cast<int>(m_layers.size())) return;
    
    Layer* top = m_layers[index].get();
    Layer* bottom = m_layers[index - 1].get();
    
    if (!top->visible) return;
    
    bottom->buffer->composite(*top->buffer, 0, 0, top->opacity);
    removeLayer(index);
}

Layer* LayerManager::getLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return nullptr;
    return m_layers[index].get();
}

const Layer* LayerManager::getLayer(int index) const {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return nullptr;
    return m_layers[index].get();
}

void LayerManager::setActiveLayer(int index) {
    if (index >= 0 && index < static_cast<int>(m_layers.size())) {
        m_activeIndex = index;
    }
}

Layer* LayerManager::getActiveLayer() {
    return getLayer(m_activeIndex);
}

void LayerManager::sampleColor(int x, int y, uint8_t* r, uint8_t* g, uint8_t* b, uint8_t* a, int mode) const {
    if (x < 0 || x >= m_width || y < 0 || y >= m_height) {
        *r = *g = *b = *a = 0;
        return;
    }

    if (mode == 1) { // Current Layer
        const Layer* l = getLayer(m_activeIndex);
        if (l) {
            const uint8_t* p = l->buffer->pixelAt(x, y);
            if (p) {
                *r = p[0]; *g = p[1]; *b = p[2]; *a = p[3];
                return;
            }
        }
    } else { // Composite
        // We could use compositeAll to a 1x1 buffer, but for many samplings 
        // a manual loop is faster.
        float fr = 0, fg = 0, fb = 0, fa = 0;
        for (const auto& layer : m_layers) {
            if (!layer->visible || layer->opacity < 0.01f) continue;
            const uint8_t* p = layer->buffer->pixelAt(x, y);
            if (!p || p[3] == 0) continue;

            float srcA = (p[3] / 255.0f) * layer->opacity;
            float invA = 1.0f - srcA;
            
            fr = p[0] * srcA + fr * invA;
            fg = p[1] * srcA + fg * invA;
            fb = p[2] * srcA + fb * invA;
            fa = srcA + fa * invA;
        }
        *r = (uint8_t)std::clamp(fr, 0.0f, 255.0f);
        *g = (uint8_t)std::clamp(fg, 0.0f, 255.0f);
        *b = (uint8_t)std::clamp(fb, 0.0f, 255.0f);
        *a = (uint8_t)std::clamp(fa * 255.0f, 0.0f, 255.0f);
        return;
    }
    *r = *g = *b = *a = 0;
}

void LayerManager::compositeAll(ImageBuffer& output) const {
    output.clear();
    
    // Composite from bottom to top
    for (const auto& layer : m_layers) {
        if (layer->visible) {
            output.composite(*layer->buffer, 0, 0, layer->opacity);
        }
    }
}

} // namespace artflow
