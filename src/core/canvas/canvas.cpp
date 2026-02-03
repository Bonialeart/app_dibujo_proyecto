/**
 * ArtFlow Studio - Canvas Implementation
 */

#include "canvas.h"
#include "../layers/layer.h"
#include "renderer.h"
#include "../brushes/brush_stroke.h"
#include <cmath>
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace artflow {

// ============================================================================
// Color Implementation
// ============================================================================

Color Color::fromHex(const std::string& hex) {
    std::string cleanHex = hex;
    if (!cleanHex.empty() && cleanHex[0] == '#') {
        cleanHex = cleanHex.substr(1);
    }
    
    if (cleanHex.length() < 6) {
        return Color(0, 0, 0, 1);
    }
    
    int r, g, b, a = 255;
    std::stringstream ss;
    
    ss << std::hex << cleanHex.substr(0, 2);
    ss >> r;
    ss.clear();
    
    ss << std::hex << cleanHex.substr(2, 2);
    ss >> g;
    ss.clear();
    
    ss << std::hex << cleanHex.substr(4, 2);
    ss >> b;
    
    if (cleanHex.length() >= 8) {
        ss.clear();
        ss << std::hex << cleanHex.substr(6, 2);
        ss >> a;
    }
    
    return Color(r / 255.0f, g / 255.0f, b / 255.0f, a / 255.0f);
}

std::string Color::toHex() const {
    std::stringstream ss;
    ss << "#";
    ss << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(r * 255);
    ss << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(g * 255);
    ss << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(b * 255);
    if (a < 1.0f) {
        ss << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(a * 255);
    }
    return ss.str();
}

Color Color::blend(const Color& other, float amount) const {
    return Color(
        r + (other.r - r) * amount,
        g + (other.g - g) * amount,
        b + (other.b - b) * amount,
        a + (other.a - a) * amount
    );
}

Color Color::withAlpha(float alpha) const {
    return Color(r, g, b, alpha);
}

// ============================================================================
// Point Implementation
// ============================================================================

float Point::distanceTo(const Point& other) const {
    float dx = other.x - x;
    float dy = other.y - y;
    return std::sqrt(dx * dx + dy * dy);
}

Point Point::lerp(const Point& other, float t) const {
    return Point(
        x + (other.x - x) * t,
        y + (other.y - y) * t,
        pressure + (other.pressure - pressure) * t
    );
}

// ============================================================================
// Rect Implementation
// ============================================================================

bool Rect::contains(const Point& p) const {
    return p.x >= x && p.x <= x + width &&
           p.y >= y && p.y <= y + height;
}

bool Rect::intersects(const Rect& other) const {
    return !(x + width < other.x || other.x + other.width < x ||
             y + height < other.y || other.y + other.height < y);
}

Rect Rect::united(const Rect& other) const {
    float minX = std::min(x, other.x);
    float minY = std::min(y, other.y);
    float maxX = std::max(x + width, other.x + other.width);
    float maxY = std::max(y + height, other.y + other.height);
    return Rect(minX, minY, maxX - minX, maxY - minY);
}

// ============================================================================
// Canvas Implementation
// ============================================================================

struct Canvas::HistoryState {
    std::vector<std::vector<uint8_t>> layerData;
    int activeLayerIndex;
};

Canvas::Canvas()
    : Canvas(CanvasConfig())
{
}

Canvas::Canvas(int width, int height)
    : m_width(width)
    , m_height(height)
    , m_dpi(300)
    , m_backgroundColor(1, 1, 1, 1)
    , m_transparentBackground(false)
    , m_activeLayerIndex(0)
    , m_viewportX(0)
    , m_viewportY(0)
    , m_zoom(1.0f)
    , m_maxHistorySize(50)
{
    m_renderer = std::make_unique<Renderer>(width, height);
    initializeDefaultLayer();
}

Canvas::Canvas(const CanvasConfig& config)
    : m_width(config.width)
    , m_height(config.height)
    , m_dpi(config.dpi)
    , m_backgroundColor(config.backgroundColor)
    , m_transparentBackground(config.transparentBackground)
    , m_activeLayerIndex(0)
    , m_viewportX(0)
    , m_viewportY(0)
    , m_zoom(1.0f)
    , m_maxHistorySize(50)
{
    m_renderer = std::make_unique<Renderer>(m_width, m_height);
    initializeDefaultLayer();
}

Canvas::~Canvas() = default;

Canvas::Canvas(Canvas&& other) noexcept = default;
Canvas& Canvas::operator=(Canvas&& other) noexcept = default;

void Canvas::initializeDefaultLayer() {
    addLayer("Background");
    if (!m_layers.empty()) {
        m_layers[0]->fill(m_backgroundColor);
    }
}

void Canvas::resize(int width, int height) {
    if (width == m_width && height == m_height) return;
    
    pushHistoryState();
    
    m_width = width;
    m_height = height;
    
    for (auto& layer : m_layers) {
        layer->resize(width, height);
    }
    
    m_renderer->resize(width, height);
    notifyEvent(CanvasEventType::CanvasResized);
}

void Canvas::setDPI(int dpi) {
    m_dpi = dpi;
}

void Canvas::setBackgroundColor(const Color& color) {
    m_backgroundColor = color;
    notifyEvent(CanvasEventType::ContentModified);
}

void Canvas::setTransparentBackground(bool transparent) {
    m_transparentBackground = transparent;
    notifyEvent(CanvasEventType::ContentModified);
}

// Layer management
int Canvas::addLayer(const std::string& name) {
    std::string layerName = name.empty() 
        ? "Layer " + std::to_string(m_layers.size() + 1)
        : name;
    
    auto layer = std::make_unique<Layer>(m_width, m_height, layerName);
    m_layers.push_back(std::move(layer));
    
    int index = static_cast<int>(m_layers.size() - 1);
    notifyEvent(CanvasEventType::LayerAdded, index);
    
    return index;
}

void Canvas::removeLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return;
    if (m_layers.size() <= 1) return; // Keep at least one layer
    
    pushHistoryState();
    
    m_layers.erase(m_layers.begin() + index);
    
    if (m_activeLayerIndex >= static_cast<int>(m_layers.size())) {
        m_activeLayerIndex = static_cast<int>(m_layers.size()) - 1;
    }
    
    notifyEvent(CanvasEventType::LayerRemoved, index);
}

void Canvas::moveLayer(int fromIndex, int toIndex) {
    if (fromIndex < 0 || fromIndex >= static_cast<int>(m_layers.size())) return;
    if (toIndex < 0 || toIndex >= static_cast<int>(m_layers.size())) return;
    if (fromIndex == toIndex) return;
    
    pushHistoryState();
    
    auto layer = std::move(m_layers[fromIndex]);
    m_layers.erase(m_layers.begin() + fromIndex);
    m_layers.insert(m_layers.begin() + toIndex, std::move(layer));
    
    if (m_activeLayerIndex == fromIndex) {
        m_activeLayerIndex = toIndex;
    }
    
    notifyEvent(CanvasEventType::LayerMoved, toIndex);
}

void Canvas::duplicateLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return;
    
    pushHistoryState();
    
    auto& sourceLayer = m_layers[index];
    auto newLayer = std::make_unique<Layer>(m_width, m_height, sourceLayer->getName() + " Copy");
    newLayer->copyFrom(*sourceLayer);
    
    m_layers.insert(m_layers.begin() + index + 1, std::move(newLayer));
    notifyEvent(CanvasEventType::LayerAdded, index + 1);
}

void Canvas::mergeLayerDown(int index) {
    if (index <= 0 || index >= static_cast<int>(m_layers.size())) return;
    
    pushHistoryState();
    
    m_layers[index - 1]->mergeWith(*m_layers[index]);
    m_layers.erase(m_layers.begin() + index);
    
    if (m_activeLayerIndex >= index) {
        m_activeLayerIndex--;
    }
    
    notifyEvent(CanvasEventType::LayerModified, index - 1);
}

void Canvas::flattenLayers() {
    if (m_layers.size() <= 1) return;
    
    pushHistoryState();
    
    auto flattenedLayer = std::make_unique<Layer>(m_width, m_height, "Flattened");
    
    if (!m_transparentBackground) {
        flattenedLayer->fill(m_backgroundColor);
    }
    
    for (const auto& layer : m_layers) {
        if (layer->isVisible()) {
            flattenedLayer->mergeWith(*layer);
        }
    }
    
    m_layers.clear();
    m_layers.push_back(std::move(flattenedLayer));
    m_activeLayerIndex = 0;
    
    notifyEvent(CanvasEventType::ContentModified);
}

Layer* Canvas::getLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return nullptr;
    return m_layers[index].get();
}

const Layer* Canvas::getLayer(int index) const {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return nullptr;
    return m_layers[index].get();
}

Layer* Canvas::getActiveLayer() {
    return getLayer(m_activeLayerIndex);
}

void Canvas::setActiveLayer(int index) {
    if (index < 0 || index >= static_cast<int>(m_layers.size())) return;
    m_activeLayerIndex = index;
}

int Canvas::getLayerCount() const {
    return static_cast<int>(m_layers.size());
}

// Drawing operations
void Canvas::beginStroke(const Point& point) {
    m_currentStroke = std::make_unique<BrushStroke>();
    m_currentStroke->addPoint(point);
    pushHistoryState();
}

void Canvas::continueStroke(const Point& point) {
    if (!m_currentStroke) return;
    m_currentStroke->addPoint(point);
    
    // Render stroke to active layer
    Layer* activeLayer = getActiveLayer();
    if (activeLayer) {
        m_currentStroke->renderTo(*activeLayer);
    }
    
    notifyEvent(CanvasEventType::ContentModified);
}

void Canvas::endStroke() {
    if (!m_currentStroke) return;
    
    Layer* activeLayer = getActiveLayer();
    if (activeLayer) {
        m_currentStroke->finalizeTo(*activeLayer);
    }
    
    m_currentStroke.reset();
}

void Canvas::cancelStroke() {
    if (!m_currentStroke) return;
    m_currentStroke.reset();
    undo(); // Restore previous state
}

// Rendering
void Canvas::render() {
    m_renderer->beginFrame();
    
    if (!m_transparentBackground) {
        m_renderer->drawBackground(m_backgroundColor);
    }
    
    for (const auto& layer : m_layers) {
        if (layer->isVisible()) {
            m_renderer->drawLayer(*layer);
        }
    }
    
    m_renderer->endFrame();
}

const uint8_t* Canvas::getPixelData() const {
    return m_renderer->getFramebufferData();
}

void Canvas::getPixelData(uint8_t* buffer, size_t bufferSize) const {
    m_renderer->getFramebufferData(buffer, bufferSize);
}

// Undo/Redo
void Canvas::pushHistoryState() {
    auto state = std::make_unique<HistoryState>();
    state->activeLayerIndex = m_activeLayerIndex;
    
    for (const auto& layer : m_layers) {
        state->layerData.push_back(layer->getData());
    }
    
    m_undoStack.push_back(std::move(state));
    
    // Limit history size
    while (m_undoStack.size() > m_maxHistorySize) {
        m_undoStack.erase(m_undoStack.begin());
    }
    
    // Clear redo stack on new action
    m_redoStack.clear();
}

void Canvas::undo() {
    if (m_undoStack.empty()) return;
    
    // Save current state to redo stack
    auto currentState = std::make_unique<HistoryState>();
    currentState->activeLayerIndex = m_activeLayerIndex;
    for (const auto& layer : m_layers) {
        currentState->layerData.push_back(layer->getData());
    }
    m_redoStack.push_back(std::move(currentState));
    
    // Restore previous state
    auto& state = m_undoStack.back();
    m_activeLayerIndex = state->activeLayerIndex;
    
    // Resize layers vector if needed
    while (m_layers.size() < state->layerData.size()) {
        addLayer();
    }
    while (m_layers.size() > state->layerData.size()) {
        m_layers.pop_back();
    }
    
    // Restore layer data
    for (size_t i = 0; i < state->layerData.size(); ++i) {
        m_layers[i]->setData(state->layerData[i]);
    }
    
    m_undoStack.pop_back();
    notifyEvent(CanvasEventType::ContentModified);
}

void Canvas::redo() {
    if (m_redoStack.empty()) return;
    
    // Save current state to undo stack
    auto currentState = std::make_unique<HistoryState>();
    currentState->activeLayerIndex = m_activeLayerIndex;
    for (const auto& layer : m_layers) {
        currentState->layerData.push_back(layer->getData());
    }
    m_undoStack.push_back(std::move(currentState));
    
    // Restore redo state
    auto& state = m_redoStack.back();
    m_activeLayerIndex = state->activeLayerIndex;
    
    while (m_layers.size() < state->layerData.size()) {
        addLayer();
    }
    while (m_layers.size() > state->layerData.size()) {
        m_layers.pop_back();
    }
    
    for (size_t i = 0; i < state->layerData.size(); ++i) {
        m_layers[i]->setData(state->layerData[i]);
    }
    
    m_redoStack.pop_back();
    notifyEvent(CanvasEventType::ContentModified);
}

bool Canvas::canUndo() const {
    return !m_undoStack.empty();
}

bool Canvas::canRedo() const {
    return !m_redoStack.empty();
}

void Canvas::clearHistory() {
    m_undoStack.clear();
    m_redoStack.clear();
}

// Viewport
void Canvas::setViewport(float x, float y, float zoom) {
    m_viewportX = x;
    m_viewportY = y;
    m_zoom = std::clamp(zoom, 0.1f, 10.0f);
}

void Canvas::setZoom(float zoom) {
    m_zoom = std::clamp(zoom, 0.1f, 10.0f);
}

// Event notification
void Canvas::setEventCallback(CanvasEventCallback callback) {
    m_eventCallback = std::move(callback);
}

void Canvas::notifyEvent(CanvasEventType type, int data) {
    if (m_eventCallback) {
        m_eventCallback(type, data);
    }
}

// File operations - stubs for now
bool Canvas::save(const std::string& path) {
    // TODO: Implement project file saving
    return false;
}

bool Canvas::load(const std::string& path) {
    // TODO: Implement project file loading
    return false;
}

bool Canvas::exportImage(const std::string& path, const std::string& format) {
    // TODO: Implement image export
    return false;
}

} // namespace artflow
