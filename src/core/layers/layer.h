/**
 * ArtFlow Studio - Layer Header
 */

#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace artflow {

struct Color;

enum class LayerBlendMode {
    Normal = 0, Multiply, Screen, Overlay, SoftLight, HardLight,
    ColorDodge, ColorBurn, Darken, Lighten, Difference
};

class Layer {
public:
    Layer(int width, int height, const std::string& name = "Layer");
    ~Layer();
    
    Layer(Layer&& other) noexcept;
    Layer& operator=(Layer&& other) noexcept;
    
    const std::string& getName() const { return m_name; }
    void setName(const std::string& name) { m_name = name; }
    
    bool isVisible() const { return m_visible; }
    void setVisible(bool visible) { m_visible = visible; }
    
    float getOpacity() const { return m_opacity; }
    void setOpacity(float opacity);
    
    LayerBlendMode getBlendMode() const { return m_blendMode; }
    void setBlendMode(LayerBlendMode mode) { m_blendMode = mode; }
    
    int getWidth() const { return m_width; }
    int getHeight() const { return m_height; }
    void resize(int width, int height);
    
    const std::vector<uint8_t>& getData() const { return m_data; }
    void setData(const std::vector<uint8_t>& data);
    
    void clear();
    void fill(const Color& color);
    void copyFrom(const Layer& other);
    void mergeWith(const Layer& other);

private:
    std::string m_name;
    int m_width, m_height;
    bool m_visible = true;
    float m_opacity = 1.0f;
    LayerBlendMode m_blendMode = LayerBlendMode::Normal;
    std::vector<uint8_t> m_data;
};

} // namespace artflow
