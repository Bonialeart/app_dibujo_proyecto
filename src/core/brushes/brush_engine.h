/**
 * ArtFlow Studio - Brush Engine Header
 */

#pragma once

#include <string>
#include <vector>
#include <memory>
#include <cstdint>

namespace artflow {

struct Point;
struct Color;
class Layer;

struct BrushSettings {
    float size = 20.0f;
    float opacity = 1.0f;
    float hardness = 0.8f;
    float spacing = 0.1f;
    float flow = 1.0f;
    float minSize = 0.1f;         // Pressure affects size
    float minOpacity = 0.1f;      // Pressure affects opacity
    bool pressureSize = true;
    bool pressureOpacity = true;
    Color color;
};

struct BrushTip {
    std::vector<float> mask;      // Grayscale mask
    int width = 0;
    int height = 0;
    bool isRound = true;
};

class BrushEngine {
public:
    BrushEngine();
    ~BrushEngine();
    
    void setSettings(const BrushSettings& settings);
    const BrushSettings& getSettings() const { return m_settings; }
    
    void setTip(const BrushTip& tip);
    void setRoundTip(float hardness = 0.8f);
    
    void beginStroke(Layer& layer, const Point& point);
    void continueStroke(Layer& layer, const Point& point);
    void endStroke(Layer& layer);
    
    void dabAt(Layer& layer, float x, float y, float pressure, float size, float opacity);

private:
    BrushSettings m_settings;
    BrushTip m_tip;
    Point m_lastPoint;
    bool m_isStroking = false;
    float m_distanceAccum = 0.0f;
    
    void generateRoundTip(int diameter, float hardness);
    void interpolateDabs(Layer& layer, const Point& from, const Point& to);
};

} // namespace artflow
