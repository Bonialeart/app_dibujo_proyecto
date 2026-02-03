from setuptools import setup, Extension
import sys
import os

# Intenta localizar pybind11
try:
    import pybind11
    pybind_include = pybind11.get_include()
except ImportError:
    print("Error: pybind11 is required to build this extension.")
    print("Run: pip install pybind11")
    sys.exit(1)

# Rutas de los archivos fuente
cpp_src_dir = os.path.join(os.getcwd(), "src")
cpp_include_dir = os.path.join(os.getcwd(), "include")
bindings_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "bindings"))
canvas_dir = os.path.abspath(os.path.join(os.getcwd(), "..", "canvas"))

sources = [
    os.path.join(bindings_dir, "python_bindings.cpp"),
    os.path.join(cpp_src_dir, "brush_engine.cpp"),
    os.path.join(cpp_src_dir, "stroke_renderer.cpp"),
    os.path.join(cpp_src_dir, "gl_utils.cpp"),
    os.path.join(cpp_src_dir, "layer_manager.cpp"),
    os.path.join(cpp_src_dir, "image_buffer.cpp"),
    os.path.join(cpp_src_dir, "color_utils.cpp"),
    os.path.join(canvas_dir, "renderer.cpp"),
]

# Verificar que los archivos existen (filtro preventivo)
existing_sources = [f for f in sources if os.path.exists(f)]

ext_modules = [
    Extension(
        "artflow_native",
        existing_sources,
        include_dirs=[
            cpp_include_dir,
            canvas_dir,
            pybind_include,
        ],
        language="c++",
        extra_compile_args=["/std:c++17", "/DNOMINMAX"] if sys.platform == "win32" else ["-std=c++17"],
        libraries=["user32", "gdi32", "opengl32"] if sys.platform == "win32" else ["GL"],
    ),
]

setup(
    name="artflow_native",
    version="1.0.0",
    author="Antigravity",
    description="Native C++ Engine for ArtFlow Watercolor Physics",
    ext_modules=ext_modules,
    zip_safe=False,
)
