/**
 * ArtFlow Studio - Canvas Header
 * High-performance drawing canvas with OpenGL acceleration
 */

#pragma once

#include <vector>
#include <memory>
#include <string>
#include <functional>
#include <cstdint>

namespace artflow {

// Forward declarations
class Layer;
class Renderer;
class BrushStroke;

/**
 * RGBA Color structure
 */
struct Color {
    float r, g, b, a;
    
    Color() : r(0), g(0), b(0), a(1) {}
    Color(float r, float g, float b, float a = 1.0f) : r(r), g(g), b(b), a(a) {}
    
    static Color fromHex(const std::string& hex);
    std::string toHex() const;
    
    Color blend(const Color& other, float amount) const;
    Color withAlpha(float alpha) const;
};

/**
 * 2D Point structure with pressure support
 */
struct Point {
    float x, y;
    float pressure;
    float tiltX, tiltY;
    uint64_t timestamp;
    
    Point() : x(0), y(0), pressure(1), tiltX(0), tiltY(0), timestamp(0) {}
    Point(float x, float y) : x(x), y(y), pressure(1), tiltX(0), tiltY(0), timestamp(0) {}
    Point(float x, float y, float pressure) : x(x), y(y), pressure(pressure), tiltX(0), tiltY(0), timestamp(0) {}
    
    float distanceTo(const Point& other) const;
    Point lerp(const Point& other, float t) const;
};

/**
 * Rectangle structure
 */
struct Rect {
    float x, y, width, height;
    
    Rect() : x(0), y(0), width(0), height(0) {}
    Rect(float x, float y, float w, float h) : x(x), y(y), width(w), height(h) {}
    
    bool contains(const Point& p) const;
    bool intersects(const Rect& other) const;
    Rect united(const Rect& other) const;
};

/**
 * Canvas configuration
 */
struct CanvasConfig {
    int width = 2048;
    int height = 2048;
    int dpi = 300;
    Color backgroundColor = Color(1, 1, 1, 1);
    bool transparentBackground = false;
};

/**
 * Canvas event types
 */
enum class CanvasEventType {
    LayerAdded,
    LayerRemoved,
    LayerMoved,
    LayerModified,
    CanvasResized,
    ContentModified
};

/**
 * Canvas event callback
 */
using CanvasEventCallback = std::function<void(CanvasEventType, int)>;

/**
 * Main Canvas class - manages layers, rendering, and drawing operations
 */
class Canvas {
public:
    Canvas();
    Canvas(int width, int height);
    Canvas(const CanvasConfig& config);
    ~Canvas();
    
    // Prevent copying
    Canvas(const Canvas&) = delete;
    Canvas& operator=(const Canvas&) = delete;
    
    // Move semantics
    Canvas(Canvas&& other) noexcept;
    Canvas& operator=(Canvas&& other) noexcept;
    
    // Canvas properties
    int getWidth() const { return m_width; }
    int getHeight() const { return m_height; }
    int getDPI() const { return m_dpi; }
    void resize(int width, int height);
    void setDPI(int dpi);
    
    // Background
    Color getBackgroundColor() const { return m_backgroundColor; }
    void setBackgroundColor(const Color& color);
    bool isTransparentBackground() const { return m_transparentBackground; }
    void setTransparentBackground(bool transparent);
    
    // Layer management
    int addLayer(const std::string& name = "");
    void removeLayer(int index);
    void moveLayer(int fromIndex, int toIndex);
    void duplicateLayer(int index);
    void mergeLayerDown(int index);
    void flattenLayers();
    
    Layer* getLayer(int index);
    const Layer* getLayer(int index) const;
    Layer* getActiveLayer();
    int getActiveLayerIndex() const { return m_activeLayerIndex; }
    void setActiveLayer(int index);
    int getLayerCount() const;
    
    // Drawing operations
    void beginStroke(const Point& point);
    void continueStroke(const Point& point);
    void endStroke();
    void cancelStroke();
    
    // Rendering
    void render();
    const uint8_t* getPixelData() const;
    void getPixelData(uint8_t* buffer, size_t bufferSize) const;
    
    // Undo/Redo
    void undo();
    void redo();
    bool canUndo() const;
    bool canRedo() const;
    void clearHistory();
    
    // File operations
    bool save(const std::string& path);
    bool load(const std::string& path);
    bool exportImage(const std::string& path, const std::string& format = "PNG");
    
    // Events
    void setEventCallback(CanvasEventCallback callback);
    
    // Viewport
    void setViewport(float x, float y, float zoom);
    float getZoom() const { return m_zoom; }
    void setZoom(float zoom);
    Point getViewportOffset() const { return Point(m_viewportX, m_viewportY); }
    
private:
    int m_width;
    int m_height;
    int m_dpi;
    Color m_backgroundColor;
    bool m_transparentBackground;
    
    std::vector<std::unique_ptr<Layer>> m_layers;
    int m_activeLayerIndex;
    
    std::unique_ptr<Renderer> m_renderer;
    std::unique_ptr<BrushStroke> m_currentStroke;
    
    // Viewport
    float m_viewportX, m_viewportY;
    float m_zoom;
    
    // Undo/Redo
    struct HistoryState;
    std::vector<std::unique_ptr<HistoryState>> m_undoStack;
    std::vector<std::unique_ptr<HistoryState>> m_redoStack;
    size_t m_maxHistorySize;
    
    // Event handling
    CanvasEventCallback m_eventCallback;
    
    void notifyEvent(CanvasEventType type, int data = 0);
    void pushHistoryState();
    void initializeDefaultLayer();
};

} // namespace artflow
