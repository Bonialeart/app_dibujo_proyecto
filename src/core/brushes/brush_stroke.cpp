/**
 * ArtFlow Studio - Brush Stroke Implementation
 */

#include "brush_stroke.h"
#include "brush_engine.h"
#include "../layers/layer.h"

namespace artflow {

BrushStroke::BrushStroke() = default;
BrushStroke::~BrushStroke() = default;

void BrushStroke::addPoint(const Point& point) {
    m_points.push_back(point);
}

void BrushStroke::renderTo(Layer& layer) {
    if (!m_engine || m_points.empty()) return;
    
    if (m_renderedUpTo == 0 && !m_points.empty()) {
        m_engine->beginStroke(layer, m_points[0]);
        m_renderedUpTo = 1;
    }
    
    for (size_t i = m_renderedUpTo; i < m_points.size(); ++i) {
        m_engine->continueStroke(layer, m_points[i]);
    }
    m_renderedUpTo = m_points.size();
}

void BrushStroke::finalizeTo(Layer& layer) {
    if (m_engine) {
        m_engine->endStroke(layer);
    }
}

void BrushStroke::clear() {
    m_points.clear();
    m_renderedUpTo = 0;
}

} // namespace artflow
