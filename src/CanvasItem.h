#ifndef CANVASITEM_H
#define CANVASITEM_H

#include <QQuickPaintedItem>
#include <QColor>
#include <QPointF>
#include <QImage>
#include <QVariantList>
#include "brush_engine.h"
#include "layer_manager.h"

class CanvasItem : public QQuickPaintedItem
{
    Q_OBJECT
    
    // Properties for QML compatibility
    Q_PROPERTY(int brushSize READ brushSize WRITE setBrushSize NOTIFY brushSizeChanged)
    Q_PROPERTY(QColor brushColor READ brushColor WRITE setBrushColor NOTIFY brushColorChanged)
    Q_PROPERTY(float brushOpacity READ brushOpacity WRITE setBrushOpacity NOTIFY brushOpacityChanged)
    Q_PROPERTY(float brushFlow READ brushFlow WRITE setBrushFlow NOTIFY brushFlowChanged)
    Q_PROPERTY(float brushHardness READ brushHardness WRITE setBrushHardness NOTIFY brushHardnessChanged)
    Q_PROPERTY(float brushSpacing READ brushSpacing WRITE setBrushSpacing NOTIFY brushSpacingChanged)
    Q_PROPERTY(float brushStabilization READ brushStabilization WRITE setBrushStabilization NOTIFY brushStabilizationChanged)
    Q_PROPERTY(float brushStreamline READ brushStreamline WRITE setBrushStreamline NOTIFY brushStreamlineChanged)
    Q_PROPERTY(float brushGrain READ brushGrain WRITE setBrushGrain NOTIFY brushGrainChanged)
    Q_PROPERTY(float brushWetness READ brushWetness WRITE setBrushWetness NOTIFY brushWetnessChanged)
    Q_PROPERTY(float brushSmudge READ brushSmudge WRITE setBrushSmudge NOTIFY brushSmudgeChanged)
    
    Q_PROPERTY(float zoomLevel READ zoomLevel WRITE setZoomLevel NOTIFY zoomLevelChanged)
    Q_PROPERTY(QString currentTool READ currentTool WRITE setCurrentTool NOTIFY currentToolChanged)
    Q_PROPERTY(int canvasWidth READ canvasWidth NOTIFY canvasWidthChanged)
    Q_PROPERTY(int canvasHeight READ canvasHeight NOTIFY canvasHeightChanged)
    Q_PROPERTY(QPointF viewOffset READ viewOffset NOTIFY viewOffsetChanged)
    Q_PROPERTY(int activeLayerIndex READ activeLayerIndex NOTIFY activeLayerChanged)
    Q_PROPERTY(bool isTransforming READ isTransforming NOTIFY isTransformingChanged)
    Q_PROPERTY(float brushAngle READ brushAngle WRITE setBrushAngle NOTIFY brushAngleChanged)
    Q_PROPERTY(float cursorRotation READ cursorRotation WRITE setCursorRotation NOTIFY cursorRotationChanged)
    Q_PROPERTY(QString currentProjectPath READ currentProjectPath NOTIFY currentProjectPathChanged)
    Q_PROPERTY(QString currentProjectName READ currentProjectName NOTIFY currentProjectNameChanged)
    Q_PROPERTY(QString brushTip READ brushTip NOTIFY brushTipChanged)
    Q_PROPERTY(QVariantList availableBrushes READ availableBrushes NOTIFY availableBrushesChanged)
    Q_PROPERTY(QString activeBrushName READ activeBrushName NOTIFY activeBrushNameChanged)

public:
    explicit CanvasItem(QQuickItem *parent = nullptr);
    ~CanvasItem() override;

    void paint(QPainter *painter) override;

    // Getters
    int brushSize() const { return m_brushSize; }
    QColor brushColor() const { return m_brushColor; }
    float brushOpacity() const { return m_brushOpacity; }
    float brushFlow() const { return m_brushFlow; }
    float brushHardness() const { return m_brushHardness; }
    float brushSpacing() const { return m_brushSpacing; }
    float brushStabilization() const { return m_brushStabilization; }
    float brushStreamline() const { return m_brushStreamline; }
    float brushGrain() const { return m_brushGrain; }
    float brushWetness() const { return m_brushWetness; }
    float brushSmudge() const { return m_brushSmudge; }
    
    float zoomLevel() const { return m_zoomLevel; }
    QString currentTool() const { return m_currentTool; }
    int canvasWidth() const { return m_canvasWidth; }
    int canvasHeight() const { return m_canvasHeight; }
    QPointF viewOffset() const { return m_viewOffset; }
    int activeLayerIndex() const { return m_activeLayerIndex; }
    bool isTransforming() const { return m_isTransforming; }
    float brushAngle() const { return m_brushAngle; }
    float cursorRotation() const { return m_cursorRotation; }
    QString currentProjectPath() const { return m_currentProjectPath; }
    QString currentProjectName() const { return m_currentProjectName; }
    QString brushTip() const { return m_brushTip; }
    QVariantList availableBrushes() const { return m_availableBrushes; }
    QString activeBrushName() const { return m_activeBrushName; }

    // Setters
    void setBrushSize(int size);
    void setBrushColor(const QColor &color);
    void setBrushOpacity(float opacity);
    void setBrushFlow(float flow);
    void setBrushHardness(float hardness);
    void setBrushSpacing(float spacing);
    void setBrushStabilization(float value);
    void setBrushStreamline(float value);
    void setBrushGrain(float value);
    void setBrushWetness(float value);
    void setBrushSmudge(float value);
    void setBrushAngle(float value);
    void setCursorRotation(float value);
    void setZoomLevel(float zoom);
    void setCurrentTool(const QString &tool);
    Q_INVOKABLE void setBackgroundColor(const QString &color);
    Q_INVOKABLE void usePreset(const QString &name);
    Q_INVOKABLE bool loadProject(const QString &path);
    Q_INVOKABLE bool saveProject(const QString &path);
    Q_INVOKABLE bool saveProjectAs(const QString &path);
    Q_INVOKABLE bool exportImage(const QString &path, const QString &format);
    Q_INVOKABLE bool importABR(const QString &path);
    Q_INVOKABLE void updateTransformProperties(float x, float y, float scale, float rotation, float w, float h);
    
    Q_INVOKABLE void resizeCanvas(int w, int h);
    Q_INVOKABLE void setProjectDpi(int dpi);
    Q_INVOKABLE QString sampleColor(int x, int y, int mode = 0);
    Q_INVOKABLE bool isLayerClipped(int index);
    Q_INVOKABLE void toggleClipping(int index);
    Q_INVOKABLE void toggleAlphaLock(int index);
    Q_INVOKABLE void toggleVisibility(int index);
    Q_INVOKABLE void clearLayer(int index);
    Q_INVOKABLE void setLayerOpacity(int index, float opacity);
    Q_INVOKABLE void setLayerBlendMode(int index, const QString &mode);
    Q_INVOKABLE void setLayerPrivate(int index, bool isPrivate);
    Q_INVOKABLE void setActiveLayer(int index);

    // Color Utilities (HCL support for Pro Sliders)
    Q_INVOKABLE QString hclToHex(float h, float c, float l);
    Q_INVOKABLE QVariantList hexToHcl(const QString &hex);

    // Q_INVOKABLE methods for Python compatibility
    Q_INVOKABLE void loadRecentProjectsAsync();
    Q_INVOKABLE QVariantList getRecentProjects(); // RE-ADDED
    Q_INVOKABLE QVariantList get_project_list();   // RE-ADDED
    Q_INVOKABLE void load_file_path(const QString &path);
    Q_INVOKABLE void handle_shortcuts(int key, int modifiers);
    Q_INVOKABLE void handle_key_release(int key);
    Q_INVOKABLE void fitToView();
    Q_INVOKABLE void addLayer();
    Q_INVOKABLE void removeLayer(int index);
    Q_INVOKABLE void duplicateLayer(int index);
    Q_INVOKABLE void mergeDown(int index);
    Q_INVOKABLE void renameLayer(int index, const QString &name);
    Q_INVOKABLE void applyEffect(int index, const QString &effect, const QVariantMap &params);
    Q_INVOKABLE QString get_brush_preview(const QString &brushName);

signals:
    void brushSizeChanged();
    void brushColorChanged();
    void brushOpacityChanged();
    void brushFlowChanged();
    void brushHardnessChanged();
    void brushSpacingChanged();
    void brushStabilizationChanged();
    void brushStreamlineChanged();
    void brushGrainChanged();
    void brushWetnessChanged();
    void brushSmudgeChanged();
    
    void zoomLevelChanged();
    void currentToolChanged();
    void canvasWidthChanged();
    void canvasHeightChanged();
    void viewOffsetChanged();
    void activeLayerChanged();
    void isTransformingChanged();
    void brushAngleChanged();
    void cursorRotationChanged();
    void currentProjectPathChanged();
    void currentProjectNameChanged();
    void brushTipChanged();
    void cursorPosChanged(float x, float y);
    void projectsLoaded(const QVariantList &projects);
    void layersChanged(const QVariantList &layers);
    void availableBrushesChanged();
    void activeBrushNameChanged();

protected:
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;
    void hoverMoveEvent(QHoverEvent *event) override;
    bool event(QEvent *event) override;

private:
    artflow::BrushEngine *m_brushEngine;
    artflow::LayerManager *m_layerManager;

    int m_brushSize;
    QColor m_brushColor;
    float m_brushOpacity;
    float m_brushFlow;
    float m_brushHardness;
    float m_brushSpacing;
    float m_brushStabilization;
    float m_brushStreamline;
    float m_brushGrain;
    float m_brushWetness;
    float m_brushSmudge;
    
    float m_zoomLevel;
    QString m_currentTool;
    int m_canvasWidth;
    int m_canvasHeight;
    QPointF m_viewOffset;
    int m_activeLayerIndex;
    bool m_isTransforming;
    float m_brushAngle;
    float m_cursorRotation;
    QString m_currentProjectPath;
    QString m_currentProjectName;
    QString m_brushTip;
    QVariantList m_availableBrushes;
    QString m_activeBrushName;
    
    QPointF m_lastPos;
    bool m_isDrawing;

    QVariantList _scanSync();
    void updateLayersList();
    void capture_timelapse_frame();
    void processDrawing(const QPointF &pos, float pressure);
};

#endif // CANVASITEM_H
