#include "CanvasItem.h"
#include <QPainter>
#include <QMouseEvent>
#include <QHoverEvent>
#include <QDebug>
#include <QtConcurrent/QtConcurrentRun>
#include <QDir>
#include <QStandardPaths>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPainterPath>
#include <QBuffer>
#include <QUrl>
#include <QFileInfo>


using namespace artflow;

CanvasItem::CanvasItem(QQuickItem *parent)
    : QQuickPaintedItem(parent)
    , m_brushSize(20)
    , m_brushColor(Qt::black)
    , m_brushOpacity(1.0f)
    , m_brushFlow(1.0f)
    , m_brushHardness(0.8f)
    , m_brushSpacing(0.1f)
    , m_brushStabilization(0.2f)
    , m_brushStreamline(0.0f)
    , m_brushGrain(0.0f)
    , m_brushWetness(0.0f)
    , m_brushSmudge(0.0f)
    , m_zoomLevel(1.0f)
    , m_currentTool("brush")
    , m_canvasWidth(1920)
    , m_canvasHeight(1080)
    , m_viewOffset(50, 50)
    , m_activeLayerIndex(0)
    , m_isTransforming(false)
    , m_brushAngle(0.0f)
    , m_cursorRotation(0.0f)
    , m_currentProjectPath("")
    , m_currentProjectName("Untitled")
    , m_brushTip("")
    , m_isDrawing(false)
{
    setAcceptHoverEvents(true);
    setAcceptedMouseButtons(Qt::AllButtons);

    m_layerManager = new LayerManager(m_canvasWidth, m_canvasHeight);
    m_brushEngine = new BrushEngine();

    m_layerManager->addLayer("Layer 1");
    m_activeLayerIndex = 1;
    m_layerManager->setActiveLayer(m_activeLayerIndex);
    
    m_availableBrushes << "Pencil HB" << "Pencil 6B" << "Ink Pen" << "Marker" 
                       << "G-Pen" << "Maru Pen" << "Watercolor" << "Watercolor Wet" 
                       << "Oil Paint" << "Acrylic" << "Soft" << "Hard" << "Mechanical"
                       << "Eraser Soft" << "Eraser Hard";
    m_activeBrushName = "Pencil HB";
    usePreset(m_activeBrushName);
    
    updateLayersList();
}

CanvasItem::~CanvasItem()
{
    delete m_brushEngine;
    delete m_layerManager;
}

void CanvasItem::paint(QPainter *painter)
{
    if (!m_layerManager) return;
    
    // Simplistic rendering of layers with blend modes and opacity
    // Note: In a full engine we'd use OpenGL for composition
    for (int i = 0; i < m_layerManager->getLayerCount(); ++i) {
        Layer* layer = m_layerManager->getLayer(i);
        if (!layer->visible) continue;

        QImage img(layer->buffer->data(), layer->buffer->width(), layer->buffer->height(), QImage::Format_RGBA8888);
        painter->setOpacity(layer->opacity);
        
        // Basic mapping for preview
        QRectF targetRect(m_viewOffset.x() * m_zoomLevel, m_viewOffset.y() * m_zoomLevel, 
                         m_canvasWidth * m_zoomLevel, m_canvasHeight * m_zoomLevel);
        painter->drawImage(targetRect, img);
    }
}

void CanvasItem::setBrushSize(int size) { 
    m_brushSize = size; 
    BrushSettings s = m_brushEngine->getBrush();
    s.size = static_cast<float>(size);
    m_brushEngine->setBrush(s);
    emit brushSizeChanged(); 
}

void CanvasItem::setBrushColor(const QColor &color) { 
    m_brushColor = color; 
    m_brushEngine->setColor(Color(color.red(), color.green(), color.blue(), color.alpha()));
    emit brushColorChanged(); 
}

void CanvasItem::setBrushOpacity(float opacity) {
    m_brushOpacity = opacity;
    BrushSettings s = m_brushEngine->getBrush();
    s.opacity = opacity;
    m_brushEngine->setBrush(s);
    emit brushOpacityChanged();
}

void CanvasItem::setBrushFlow(float flow) {
    m_brushFlow = flow;
    BrushSettings s = m_brushEngine->getBrush();
    s.flow = flow;
    m_brushEngine->setBrush(s);
    emit brushFlowChanged();
}

void CanvasItem::setBrushHardness(float hardness) {
    m_brushHardness = hardness;
    BrushSettings s = m_brushEngine->getBrush();
    s.hardness = hardness;
    m_brushEngine->setBrush(s);
    emit brushHardnessChanged();
}

void CanvasItem::setBrushSpacing(float spacing) {
    m_brushSpacing = spacing;
    BrushSettings s = m_brushEngine->getBrush();
    s.spacing = spacing;
    m_brushEngine->setBrush(s);
    emit brushSpacingChanged();
}

void CanvasItem::setBrushStabilization(float value) {
    m_brushStabilization = value;
    BrushSettings s = m_brushEngine->getBrush();
    s.stabilization = value;
    m_brushEngine->setBrush(s);
    emit brushStabilizationChanged();
}

void CanvasItem::setBrushStreamline(float value) {
    m_brushStreamline = value;
    BrushSettings s = m_brushEngine->getBrush();
    s.streamline = value;
    m_brushEngine->setBrush(s);
    emit brushStreamlineChanged();
}

void CanvasItem::setBrushGrain(float value) {
    m_brushGrain = value;
    BrushSettings s = m_brushEngine->getBrush();
    s.grain = value;
    m_brushEngine->setBrush(s);
    emit brushGrainChanged();
}

void CanvasItem::setBrushWetness(float value) {
    m_brushWetness = value;
    BrushSettings s = m_brushEngine->getBrush();
    s.wetness = value;
    m_brushEngine->setBrush(s);
    emit brushWetnessChanged();
}

void CanvasItem::setBrushSmudge(float value) {
    m_brushSmudge = value;
    BrushSettings s = m_brushEngine->getBrush();
    s.smudge = value;
    m_brushEngine->setBrush(s);
    emit brushSmudgeChanged();
}

void CanvasItem::setBrushAngle(float value) {
    m_brushAngle = value;
    emit brushAngleChanged();
}

void CanvasItem::setCursorRotation(float value) {
    m_cursorRotation = value;
    emit cursorRotationChanged();
}

void CanvasItem::setZoomLevel(float zoom) { m_zoomLevel = zoom; emit zoomLevelChanged(); update(); }
void CanvasItem::setCurrentTool(const QString &tool) { m_currentTool = tool; emit currentToolChanged(); }

void CanvasItem::loadRecentProjectsAsync()
{
    QtConcurrent::run([this]() {
        QVariantList results = this->_scanSync();
        emit projectsLoaded(results);
    });
}

QVariantList CanvasItem::getRecentProjects()
{
    QVariantList full = _scanSync();
    if (full.size() > 5) return full.mid(0, 5);
    return full;
}

QVariantList CanvasItem::get_project_list()
{
    return _scanSync();
}

QVariantList CanvasItem::_scanSync()
{
    QVariantList results;
    QString path = QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation) + "/ArtFlowProjects";
    QDir dir(path);
    
    QFileInfoList entries = dir.entryInfoList(QDir::Dirs | QDir::Files | QDir::NoDotAndDotDot, QDir::Time);
    for (const QFileInfo &info : entries) {
        if (info.fileName().endsWith(".json") && info.isFile()) continue;
        
        QVariantMap item;
        item["name"] = info.fileName();
        item["path"] = info.absoluteFilePath();
        item["type"] = info.isDir() ? "folder" : "drawing";
        item["date"] = info.lastModified();
        results.append(item);
    }
    return results;
}

void CanvasItem::load_file_path(const QString &path) { loadProject(path); }
void CanvasItem::handle_shortcuts(int key, int modifiers) { qDebug() << "Shortcut:" << key; }
void CanvasItem::handle_key_release(int key) {}
void CanvasItem::fitToView() { qDebug() << "Fitting to view"; }

void CanvasItem::addLayer()
{
    m_layerManager->addLayer("New Layer");
    m_activeLayerIndex = m_layerManager->getLayerCount() - 1;
    emit activeLayerChanged();
    updateLayersList();
    update();
}

void CanvasItem::removeLayer(int index)
{
    m_layerManager->removeLayer(index);
    m_activeLayerIndex = qMax(0, (int)m_layerManager->getLayerCount() - 1);
    emit activeLayerChanged();
    updateLayersList();
    update();
}

void CanvasItem::duplicateLayer(int index)
{
    m_layerManager->duplicateLayer(index);
    updateLayersList();
    update();
}

void CanvasItem::mergeDown(int index)
{
    m_layerManager->mergeDown(index);
    updateLayersList();
    update();
}

void CanvasItem::renameLayer(int index, const QString &name)
{
    Layer* l = m_layerManager->getLayer(index);
    if (l) l->name = name.toStdString();
}

void CanvasItem::applyEffect(int index, const QString &effect, const QVariantMap &params)
{
    qDebug() << "Applying effect:" << effect << "on layer" << index;
}

void CanvasItem::setBackgroundColor(const QString &color) {
    qDebug() << "Setting background color:" << color;
    // In a real app we'd update the bottom layer or a special background property
}



bool CanvasItem::loadProject(const QString &path) {
    qDebug() << "Loading project from:" << path;
    m_currentProjectPath = path;
    m_currentProjectName = QFileInfo(path).baseName();
    emit currentProjectPathChanged();
    emit currentProjectNameChanged();
    
    // In a real app, you'd load layers from file here
    return true; 
}

bool CanvasItem::saveProject(const QString &path) {
    qDebug() << "Saving project to:" << path;
    return true;
}

bool CanvasItem::saveProjectAs(const QString &path) {
    return saveProject(path);
}

bool CanvasItem::exportImage(const QString &path, const QString &format) {
    if (!m_layerManager) return false;
    
    // Create a composite image
    ImageBuffer composite(m_canvasWidth, m_canvasHeight);
    m_layerManager->compositeAll(composite);
    
    QImage img(composite.data(), m_canvasWidth, m_canvasHeight, QImage::Format_RGBA8888);
    // Convert path to local file if it's a URL
    QString localPath = path;
    if (localPath.startsWith("file:///")) {
        localPath = QUrl(path).toLocalFile();
    }
    
    return img.save(localPath, format.toUpper().toStdString().c_str());
}

bool CanvasItem::importABR(const QString &path) {
    qDebug() << "Importing ABR:" << path;
    return true;
}

void CanvasItem::updateTransformProperties(float x, float y, float scale, float rotation, float w, float h) {
    // This would update the transformation matrix for a selection
}

void CanvasItem::updateLayersList() {
    if (!m_layerManager) return;
    
    QVariantList layerList;
    for (int i = 0; i < m_layerManager->getLayerCount(); ++i) {
        Layer* l = m_layerManager->getLayer(i);
        QVariantMap layer;
    layer["layerId"] = i;
    layer["name"] = QString::fromStdString(l->name);
    layer["visible"] = l->visible;
    layer["opacity"] = l->opacity;
    layer["locked"] = l->locked;
    layer["alpha_lock"] = l->alphaLock;
    layer["clipped"] = l->clipped;
    layer["active"] = (i == m_activeLayerIndex);
    layer["type"] = (i == 0) ? "background" : "drawing"; 
    layer["thumbnail"] = ""; 
    layerList.prepend(layer); 
    }
    emit layersChanged(layerList);
}

void CanvasItem::resizeCanvas(int w, int h) {
    m_canvasWidth = w;
    m_canvasHeight = h;
    
    delete m_layerManager;
    m_layerManager = new LayerManager(w, h);
    
    m_layerManager->addLayer("Layer 1");
    m_activeLayerIndex = 1;
    m_layerManager->setActiveLayer(m_activeLayerIndex);
    
    emit canvasWidthChanged();
    emit canvasHeightChanged();
    updateLayersList();
    update();
}

void CanvasItem::setProjectDpi(int dpi) {
    qDebug() << "DPI set to" << dpi;
}

QString CanvasItem::sampleColor(int x, int y, int mode) {
    if (!m_layerManager) return "#000000";
    
    uint8_t r, g, b, a;
    float cx = (x - m_viewOffset.x() * m_zoomLevel) / m_zoomLevel;
    float cy = (y - m_viewOffset.y() * m_zoomLevel) / m_zoomLevel;
    
    m_layerManager->sampleColor(static_cast<int>(cx), static_cast<int>(cy), &r, &g, &b, &a, mode);
    return QColor(r, g, b, a).name();
}

bool CanvasItem::isLayerClipped(int index) {
    Layer* l = m_layerManager->getLayer(index);
    return l ? l->clipped : false;
}

void CanvasItem::toggleClipping(int index) {
    Layer* l = m_layerManager->getLayer(index);
    if (l) {
        l->clipped = !l->clipped;
        updateLayersList();
        update();
    }
}

void CanvasItem::toggleAlphaLock(int index) {
    Layer* l = m_layerManager->getLayer(index);
    if (l) {
        l->alphaLock = !l->alphaLock;
        updateLayersList();
    }
}

void CanvasItem::toggleVisibility(int index) {
    Layer* l = m_layerManager->getLayer(index);
    if (l) {
        l->visible = !l->visible;
        updateLayersList();
        update();
    }
}

void CanvasItem::clearLayer(int index) {
    Layer* l = m_layerManager->getLayer(index);
    if (l) {
        l->buffer->clear();
        update();
    }
}

void CanvasItem::setLayerOpacity(int index, float opacity) {
    Layer* l = m_layerManager->getLayer(index);
    if (l) {
        l->opacity = opacity;
        updateLayersList();
        update();
    }
}

void CanvasItem::setLayerBlendMode(int index, const QString &mode) {
    Layer* l = m_layerManager->getLayer(index);
    if (l) {
        if (mode == "Normal") l->blendMode = BlendMode::Normal;
        else if (mode == "Multiply") l->blendMode = BlendMode::Multiply;
        else if (mode == "Screen") l->blendMode = BlendMode::Screen;
        else if (mode == "Overlay") l->blendMode = BlendMode::Overlay;
        
        updateLayersList();
        update();
    }
}

void CanvasItem::setActiveLayer(int index) {
    if (m_layerManager && index >= 0 && index < m_layerManager->getLayerCount()) {
        m_activeLayerIndex = index;
        m_layerManager->setActiveLayer(index);
        emit activeLayerChanged();
    }
}

QString CanvasItem::hclToHex(float h, float c, float l) {
    const float PI = 3.14159265358979323846f;
    float h_rad = h * (PI / 180.0f);
    float L_norm = l / 100.0f;
    float C_norm = c / 100.0f;
    
    float r = L_norm + C_norm * cos(h_rad);
    float g = L_norm - C_norm * 0.5f; 
    float b = L_norm + C_norm * sin(h_rad);
    
    QColor color;
    color.setRgbF(std::clamp(r, 0.0f, 1.0f), 
                  std::clamp(g, 0.0f, 1.0f), 
                  std::clamp(b, 0.0f, 1.0f));
    return color.name();
}

QVariantList CanvasItem::hexToHcl(const QString &hex) {
    QColor col(hex);
    float r = col.redF();
    float g = col.greenF();
    float b = col.blueF();
    
    float l = (0.299f * col.red() + 0.587f * col.green() + 0.114f * col.blue()) / 255.0f;
    
    float h = col.hsvHueF();
    if (h < 0) h = 0;
    
    float s = col.hsvSaturationF();
    float v = col.valueF();
    float ch = s * v;
    
    return QVariantList() << h * 360.0f << ch * 100.0f << l * 100.0f;
}

void CanvasItem::usePreset(const QString &name) {
    m_activeBrushName = name;
    emit activeBrushNameChanged();
    
    BrushSettings s = m_brushEngine->getBrush();
    s.wetness = 0.0f;
    s.smudge = 0.0f;
    s.jitter = 0.0f;
    s.spacing = 0.1f;
    s.hardness = 0.8f;

    if (name == "Pencil HB") {
        setBrushSize(4); setBrushOpacity(0.5f); setBrushHardness(0.1f); setBrushSpacing(0.05f);
        s.type = BrushSettings::Type::Pencil;
        s.grain = 0.6f;
    } else if (name == "Pencil 6B") {
        setBrushSize(15); setBrushOpacity(0.85f); setBrushHardness(0.4f); setBrushSpacing(0.05f);
        s.type = BrushSettings::Type::Pencil;
        s.grain = 0.9f;
    } else if (name == "Ink Pen") {
        setBrushSize(12); setBrushOpacity(1.0f); setBrushHardness(1.0f); setBrushSpacing(0.02f);
        s.type = BrushSettings::Type::Ink;
    } else if (name == "G-Pen") {
        setBrushSize(15); setBrushOpacity(1.0f); setBrushHardness(0.98f); setBrushSpacing(0.02f);
        s.type = BrushSettings::Type::Ink;
    } else if (name == "Watercolor") {
        setBrushSize(45); setBrushOpacity(0.35f); setBrushHardness(0.25f); setBrushSpacing(0.1f);
        s.type = BrushSettings::Type::Watercolor;
        s.wetness = 0.4f;
    } else if (name == "Watercolor Wet") {
        setBrushSize(55); setBrushOpacity(0.3f); setBrushHardness(0.1f); setBrushSpacing(0.1f);
        s.type = BrushSettings::Type::Watercolor;
        s.wetness = 0.9f;
    } else if (name == "Oil Paint") {
        setBrushSize(35); setBrushOpacity(1.0f); setBrushHardness(0.8f); setBrushSpacing(0.02f);
        s.type = BrushSettings::Type::Oil;
        s.smudge = 0.8f;
    } else if (name == "Acrylic") {
        setBrushSize(35); setBrushOpacity(0.95f); setBrushHardness(0.9f); setBrushSpacing(0.02f);
        s.type = BrushSettings::Type::Oil;
        s.smudge = 0.6f;
    } else if (name == "Soft") {
        setBrushSize(60); setBrushOpacity(0.15f); setBrushHardness(0.0f);
        s.type = BrushSettings::Type::Airbrush;
    } else if (name == "Hard") {
        setBrushSize(40); setBrushOpacity(0.2f); setBrushHardness(0.85f);
        s.type = BrushSettings::Type::Airbrush;
    } else if (name == "Eraser Soft") {
        setBrushSize(40); setBrushOpacity(1.0f); setBrushHardness(0.2f);
        s.type = BrushSettings::Type::Eraser;
    } else if (name == "Eraser Hard") {
        setBrushSize(20); setBrushOpacity(1.0f); setBrushHardness(0.95f);
        s.type = BrushSettings::Type::Eraser;
    }
    
    m_brushEngine->setBrush(s);
}

QString CanvasItem::get_brush_preview(const QString &brushName) {
    QImage img(220, 100, QImage::Format_Alpha8);
    img.fill(0);
    
    QPainter painter(&img);
    painter.setRenderHint(QPainter::Antialiasing);
    
    QPainterPath path;
    path.moveTo(30, 70);
    path.cubicTo(80, 10, 140, 90, 190, 30);
    
    // Simple preview stroke
    painter.setPen(QPen(Qt::white, 4));
    painter.drawPath(path);
    painter.end();
    
    QByteArray ba;
    QBuffer buffer(&ba);
    buffer.open(QIODevice::WriteOnly);
    img.save(&buffer, "PNG");
    
    return "data:image/png;base64," + ba.toBase64();
}

void CanvasItem::capture_timelapse_frame() {
    if (!m_layerManager) return;
    
    static int frameCount = 0;
    QString path = QStandardPaths::writableLocation(QStandardPaths::PicturesLocation) + "/ArtFlow/Timelapse";
    QDir().mkpath(path);
    
    QString fileName = QString("%1/frame_%2.jpg").arg(path).arg(frameCount++, 6, 10, QChar('0'));
    
    ImageBuffer composite(m_canvasWidth, m_canvasHeight);
    m_layerManager->compositeAll(composite);
    
    QImage img(composite.data(), m_canvasWidth, m_canvasHeight, QImage::Format_RGBA8888);
    img.save(fileName, "JPG", 85);
}

void CanvasItem::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        m_isDrawing = true;
        m_lastPos = (event->position() - m_viewOffset * m_zoomLevel) / m_zoomLevel;
        
        Layer* layer = m_layerManager->getActiveLayer();
        if (layer) {
            ImageBuffer* mask = nullptr;
            if (layer->clipped && m_activeLayerIndex > 0) {
                Layer* parent = m_layerManager->getLayer(m_activeLayerIndex - 1);
                if (parent) mask = parent->buffer.get();
            }

            m_brushEngine->beginStroke(StrokePoint(m_lastPos.x(), m_lastPos.y()));
            m_brushEngine->renderDab(*(layer->buffer), m_lastPos.x(), m_lastPos.y(), 1.0f, layer->alphaLock, mask);
            update();
        }
    }
}

void CanvasItem::mouseMoveEvent(QMouseEvent *event)
{
    QPointF currentPos = (event->position() - m_viewOffset * m_zoomLevel) / m_zoomLevel;
    emit cursorPosChanged(event->position().x(), event->position().y());

    if (m_isDrawing) {
        Layer* layer = m_layerManager->getActiveLayer();
        if (layer) {
            ImageBuffer* mask = nullptr;
            if (layer->clipped && m_activeLayerIndex > 0) {
                Layer* parent = m_layerManager->getLayer(m_activeLayerIndex - 1);
                if (parent) mask = parent->buffer.get();
            }

            m_brushEngine->renderStrokeSegment(*(layer->buffer), 
                StrokePoint(m_lastPos.x(), m_lastPos.y()), 
                StrokePoint(currentPos.x(), currentPos.y()),
                layer->alphaLock, mask);
            m_lastPos = currentPos;
            update();
        }
    }
}

void CanvasItem::mouseReleaseEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        m_isDrawing = false;
        m_brushEngine->endStroke();
        capture_timelapse_frame();
    }
}

void CanvasItem::hoverMoveEvent(QHoverEvent *event) {
    emit cursorPosChanged(event->position().x(), event->position().y());
}
