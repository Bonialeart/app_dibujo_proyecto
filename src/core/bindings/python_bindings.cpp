/**
 * ArtFlow Studio - Python Bindings
 * Exposes C++ core to Python via pybind11
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "brush_engine.h"
#include "image_buffer.h"
#include "layer_manager.h"
#include "color_utils.h"
#include "stroke_renderer.h"
#include "../canvas/renderer.h"
#include "../brushes/abr_parser.h"

namespace py = pybind11;
using namespace artflow;

PYBIND11_MODULE(artflow_native, m) {
    m.doc() = "ArtFlow Studio Native Core - High-performance drawing engine";

    // Color struct
    py::class_<Color>(m, "Color")
        .def(py::init<>())
        .def(py::init<uint8_t, uint8_t, uint8_t, uint8_t>(),
             py::arg("r"), py::arg("g"), py::arg("b"), py::arg("a") = 255)
        .def_readwrite("r", &Color::r)
        .def_readwrite("g", &Color::g)
        .def_readwrite("b", &Color::b)
        .def_readwrite("a", &Color::a)
        .def("blend", &Color::blend);

    // StrokePoint struct
    py::class_<StrokePoint>(m, "StrokePoint")
        .def(py::init<>())
        .def(py::init<float, float, float>(),
             py::arg("x"), py::arg("y"), py::arg("pressure") = 1.0f)
        .def_readwrite("x", &StrokePoint::x)
        .def_readwrite("y", &StrokePoint::y)
        .def_readwrite("pressure", &StrokePoint::pressure)
        .def_readwrite("tiltX", &StrokePoint::tiltX)
        .def_readwrite("tiltY", &StrokePoint::tiltY);

    // BrushSettings
    py::class_<BrushSettings>(m, "BrushSettings")
        .def(py::init<>())
        .def_readwrite("size", &BrushSettings::size)
        .def_readwrite("opacity", &BrushSettings::opacity)
        .def_readwrite("hardness", &BrushSettings::hardness)
        .def_readwrite("flow", &BrushSettings::flow)
        .def_readwrite("spacing", &BrushSettings::spacing)
        .def_readwrite("grain", &BrushSettings::grain)
        .def_readwrite("jitter", &BrushSettings::jitter)
        .def_readwrite("stabilization", &BrushSettings::stabilization)
        .def_readwrite("rotation", &BrushSettings::rotation)
        .def_readwrite("rotateWithStroke", &BrushSettings::rotateWithStroke)
        .def_readwrite("textureId", &BrushSettings::textureId)
        .def_readwrite("textureScale", &BrushSettings::textureScale)
        .def_readwrite("sizeByPressure", &BrushSettings::sizeByPressure)
        .def_readwrite("opacityByPressure", &BrushSettings::opacityByPressure);

    // BrushSettings::Type enum
    py::enum_<BrushSettings::Type>(m, "BrushType")
        .value("Round", BrushSettings::Type::Round)
        .value("Pencil", BrushSettings::Type::Pencil)
        .value("Airbrush", BrushSettings::Type::Airbrush)
        .value("Ink", BrushSettings::Type::Ink)
        .value("Watercolor", BrushSettings::Type::Watercolor)
        .value("Oil", BrushSettings::Type::Oil)
        .value("Eraser", BrushSettings::Type::Eraser)
        .value("Custom", BrushSettings::Type::Custom);

    // ImageBuffer
    py::class_<ImageBuffer>(m, "ImageBuffer")
        .def(py::init<int, int>())
        .def("width", &ImageBuffer::width)
        .def("height", &ImageBuffer::height)
        .def("setPixel", &ImageBuffer::setPixel)
        .def("fill", &ImageBuffer::fill)
        .def("clear", &ImageBuffer::clear)
        .def("blendPixel", &ImageBuffer::blendPixel)
        .def("drawCircle", &ImageBuffer::drawCircle,
             py::arg("cx"), py::arg("cy"), py::arg("radius"),
             py::arg("r"), py::arg("g"), py::arg("b"), py::arg("a"),
             py::arg("hardness") = 1.0f, py::arg("grain") = 0.0f)
        .def("drawStrokeTextured", &ImageBuffer::drawStrokeTextured,
             py::arg("x1"), py::arg("y1"), py::arg("x2"), py::arg("y2"),
             py::arg("stamp"), py::arg("spacing"), py::arg("opacity"),
             py::arg("rotate") = true, py::arg("angle_jitter") = 0.0f,
             py::arg("is_watercolor") = false,
             py::arg("paper_texture") = nullptr)
        .def("getBytes", &ImageBuffer::getBytes);

    // BrushEngine
    py::class_<BrushEngine>(m, "BrushEngine")
        .def(py::init<>())
        .def("setBrush", &BrushEngine::setBrush)
        .def("getBrush", &BrushEngine::getBrush, py::return_value_policy::reference)
        .def("setColor", &BrushEngine::setColor)
        .def("getColor", &BrushEngine::getColor, py::return_value_policy::reference)
        .def("beginStroke", &BrushEngine::beginStroke)
        .def("continueStroke", &BrushEngine::continueStroke)
        .def("endStroke", &BrushEngine::endStroke)
        .def("renderDab", &BrushEngine::renderDab)
        .def("renderStrokeSegment", &BrushEngine::renderStrokeSegment);

    // BlendMode enum
    py::enum_<BlendMode>(m, "BlendMode")
        .value("Normal", BlendMode::Normal)
        .value("Multiply", BlendMode::Multiply)
        .value("Screen", BlendMode::Screen)
        .value("Overlay", BlendMode::Overlay)
        .value("SoftLight", BlendMode::SoftLight)
        .value("HardLight", BlendMode::HardLight)
        .value("ColorDodge", BlendMode::ColorDodge)
        .value("ColorBurn", BlendMode::ColorBurn)
        .value("Darken", BlendMode::Darken)
        .value("Lighten", BlendMode::Lighten);

    // Layer
    py::class_<Layer>(m, "Layer")
        .def_readwrite("name", &Layer::name)
        .def_readwrite("opacity", &Layer::opacity)
        .def_readwrite("blendMode", &Layer::blendMode)
        .def_readwrite("visible", &Layer::visible)
        .def_readwrite("locked", &Layer::locked);

    // LayerManager
    py::class_<LayerManager>(m, "LayerManager")
        .def(py::init<int, int>())
        .def("addLayer", &LayerManager::addLayer)
        .def("removeLayer", &LayerManager::removeLayer)
        .def("moveLayer", &LayerManager::moveLayer)
        .def("duplicateLayer", &LayerManager::duplicateLayer)
        .def("mergeDown", &LayerManager::mergeDown)
        .def("getLayer", static_cast<Layer* (LayerManager::*)(int)>(&LayerManager::getLayer),
             py::return_value_policy::reference)
        .def("getLayerCount", &LayerManager::getLayerCount)
        .def("setActiveLayer", &LayerManager::setActiveLayer)
        .def("getActiveLayerIndex", &LayerManager::getActiveLayerIndex)
        .def("compositeAll", &LayerManager::compositeAll)
        .def("width", &LayerManager::width)
        .def("height", &LayerManager::height);

    // Color utilities
    m.def("rgbToHsv", &color::rgbToHsv, "Convert RGB to HSV");
    m.def("hsvToRgb", &color::hsvToRgb, "Convert HSV to RGB");
    m.def("rgbToHsl", &color::rgbToHsl, "Convert RGB to HSL");
    m.def("hslToRgb", &color::hslToRgb, "Convert HSL to RGB");
    m.def("luminance", &color::luminance, "Calculate perceived luminance");

    // --- PRO OPENGL ENGINE BINDINGS ---
    
    // StrokeRenderer (GPU Splatting)
    py::class_<StrokeRenderer>(m, "StrokeRenderer")
        .def(py::init<>())
        .def("initialize", &StrokeRenderer::initialize)
        .def("beginFrame", &StrokeRenderer::beginFrame)
        .def("endFrame", &StrokeRenderer::endFrame)
        .def("drawDab", [](StrokeRenderer& self, float x, float y, float size, float rotation, 
                           const std::vector<float>& color, float hardness, float pressure, int mode) {
             float r=0,g=0,b=0,a=1;
             if(color.size()>=3) { r=color[0]; g=color[1]; b=color[2]; }
             if(color.size()>=4) { a=color[3]; }
             self.drawDab(x, y, size, rotation, r, g, b, a, hardness, pressure, mode);
        })
        .def("drawDabPingPong", [](StrokeRenderer& self, float x, float y, float size, float rotation, 
                                   const std::vector<float>& color, float hardness, float pressure, int mode,
                                   unsigned int canvasTex, unsigned int wetMap) {
             float r=0,g=0,b=0,a=1;
             if(color.size()>=3) { r=color[0]; g=color[1]; b=color[2]; }
             if(color.size()>=4) { a=color[3]; }
             self.drawDabPingPong(x, y, size, rotation, r, g, b, a, hardness, pressure, mode, canvasTex, wetMap);
        })
        .def("setBrushTip", [](StrokeRenderer& self, py::bytes data, int w, int h) {
            std::string s = data;
            self.setBrushTip((const unsigned char*)s.data(), w, h);
        })
        .def("setPaperTexture", [](StrokeRenderer& self, py::bytes data, int w, int h) {
            std::string s = data;
            self.setPaperTexture((const unsigned char*)s.data(), w, h);
        });

    // Renderer (FBO / Ping-Pong Manager)
    py::class_<Renderer>(m, "Renderer")
        .def(py::init<int, int>())
        // initializeOpenGL removed (automatic in constructor)
        .def("beginFrame", &Renderer::beginFrame)
        .def("endFrame", &Renderer::endFrame)
        .def("swapBuffers", &Renderer::swapBuffers)
        .def("getTargetFBO", &Renderer::getTargetFBO)
        .def("getSourceTexture", &Renderer::getSourceTexture)
        .def("setBufferData", [](Renderer& self, py::bytes data) {
            std::string s = data;
            self.setBufferData((const uint8_t*)s.data());
        })
        .def("resize", &Renderer::resize)
        .def("getWidth", &Renderer::getWidth)
        .def("getHeight", &Renderer::getHeight);

    // --- ABR PARSER BINDINGS ---
    py::class_<ABRBrush>(m, "ABRBrush")
        .def_readonly("name", &ABRBrush::name)
        .def_readonly("diameter", &ABRBrush::diameter) 
        .def_readonly("spacing", &ABRBrush::spacing)
        .def_readonly("angle", &ABRBrush::angle)
        .def_readonly("roundness", &ABRBrush::roundness)
        .def_readonly("patternWidth", &ABRBrush::patternWidth)
        .def_readonly("patternHeight", &ABRBrush::patternHeight)
        .def("getPattern", [](const ABRBrush& self) {
             return py::bytes(reinterpret_cast<const char*>(self.pattern.data()), self.pattern.size());
        });

    py::class_<ABRFile>(m, "ABRFile")
        .def_readonly("version", &ABRFile::version)
        .def_readonly("brushes", &ABRFile::brushes);

    py::class_<ABRParser>(m, "ABRParser")
        .def_static("parse", &ABRParser::parse)
        .def_static("isValid", &ABRParser::isValidABR);
}
