/**
 * ArtFlow Studio - Layer Manager Implementation
 */

#include "layer_manager.h"
#include <algorithm>

namespace artflow {

Layer::Layer(const std::string& name, int width, int height)
    : name(name), buffer(std::make_unique<ImageBuffer>(width, height)) {
}

LayerManager::LayerManager(int width, int height)
    : m_width(width), m_height(height) {
    // Create default background layer
    addLayer("Background");
}

LayerManager::~LayerManager() = default;

int LayerManager::addLayer(const std::string& name) {
    auto layer = std::make_unique<Layer>(name, m_width, m_height);
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
    newLayer->opacity = src->opacity;
    newLayer->blendMode = src->blendMode;
    newLayer->visible = src->visible;
    
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
