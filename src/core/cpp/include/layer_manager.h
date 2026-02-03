/**
 * ArtFlow Studio - Layer Manager
 * Layer stack management for compositing
 */

#pragma once

#include "image_buffer.h"
#include <vector>
#include <memory>
#include <string>

namespace artflow {

// Blend modes (like Photoshop)
enum class BlendMode {
    Normal,
    Multiply,
    Screen,
    Overlay,
    SoftLight,
    HardLight,
    ColorDodge,
    ColorBurn,
    Darken,
    Lighten,
    Difference,
    Exclusion
};

/**
 * Layer - Single layer with buffer and properties
 */
struct Layer {
    std::string name;
    std::unique_ptr<ImageBuffer> buffer;
    float opacity = 1.0f;
    BlendMode blendMode = BlendMode::Normal;
    bool visible = true;
    bool locked = false;
    
    Layer(const std::string& name, int width, int height);
};

/**
 * LayerManager - Manages layer stack and compositing
 */
class LayerManager {
public:
    LayerManager(int width, int height);
    ~LayerManager();
    
    // Layer operations
    int addLayer(const std::string& name);
    void removeLayer(int index);
    void moveLayer(int fromIndex, int toIndex);
    void duplicateLayer(int index);
    void mergeDown(int index);
    
    // Access layers
    Layer* getLayer(int index);
    const Layer* getLayer(int index) const;
    int getLayerCount() const { return static_cast<int>(m_layers.size()); }
    
    // Active layer
    void setActiveLayer(int index);
    int getActiveLayerIndex() const { return m_activeIndex; }
    Layer* getActiveLayer();
    
    // Composite all visible layers
    void compositeAll(ImageBuffer& output) const;
    
    // Canvas dimensions
    int width() const { return m_width; }
    int height() const { return m_height; }

private:
    int m_width;
    int m_height;
    std::vector<std::unique_ptr<Layer>> m_layers;
    int m_activeIndex = 0;
    
    // Apply blend mode between two colors
    static void blendColors(uint8_t* dst, const uint8_t* src, BlendMode mode, float opacity);
};

} // namespace artflow
