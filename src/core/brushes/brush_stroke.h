/**
 * ArtFlow Studio - Brush Stroke Header
 */

#pragma once

#include <vector>
#include "../canvas/canvas.h"

namespace artflow {

class Layer;
class BrushEngine;

class BrushStroke {
public:
    BrushStroke();
    ~BrushStroke();
    
    void setBrushEngine(BrushEngine* engine) { m_engine = engine; }
    void addPoint(const Point& point);
    void renderTo(Layer& layer);
    void finalizeTo(Layer& layer);
    void clear();
    
    const std::vector<Point>& getPoints() const { return m_points; }
    bool isEmpty() const { return m_points.empty(); }

private:
    std::vector<Point> m_points;
    BrushEngine* m_engine = nullptr;
    size_t m_renderedUpTo = 0;
};

} // namespace artflow
