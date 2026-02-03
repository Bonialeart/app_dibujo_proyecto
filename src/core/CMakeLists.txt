cmake_minimum_required(VERSION 3.20)
project(ArtFlowCore VERSION 1.0.0 LANGUAGES CXX)

# Fix Policy CMP0148 warning (FindPythonInterp/Libs removed in newer CMake)
if(POLICY CMP0148)
    cmake_policy(SET CMP0148 NEW)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Find required packages
find_package(OpenGL REQUIRED)

# Find Python first to help pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Find pybind11 - try standard search first
find_package(pybind11 CONFIG QUIET)

if(NOT pybind11_FOUND)
    # Try to find it via python if pip-installed
    execute_process(
        COMMAND "${Python3_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
        OUTPUT_VARIABLE pybind11_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if(pybind11_DIR)
        message(STATUS "Found pybind11 via python: ${pybind11_DIR}")
        find_package(pybind11 CONFIG REQUIRED)
    else()
        # Fallback to FetchContent
        message(STATUS "pybind11 not found, downloading via FetchContent...")
        include(FetchContent)
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG v2.12.0
        )
        FetchContent_MakeAvailable(pybind11)
    endif()
endif()

# Include directories
set(CORE_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/cpp/include
    ${CMAKE_CURRENT_SOURCE_DIR}/canvas
    ${CMAKE_CURRENT_SOURCE_DIR}/brushes
    ${CMAKE_CURRENT_SOURCE_DIR}/layers
    ${OPENGL_INCLUDE_DIR}
)

include_directories(${CORE_INCLUDE_DIRS})

# Source files
set(CANVAS_SOURCES
    canvas/canvas.cpp
    canvas/renderer.cpp
    cpp/src/gl_utils.cpp
    cpp/src/stroke_renderer.cpp
    cpp/src/image_buffer.cpp
)

set(BRUSH_SOURCES
    cpp/src/brush_engine.cpp
    brushes/brush_stroke.cpp
    brushes/abr_parser.cpp
)

set(LAYER_SOURCES
    layers/layer.cpp
    cpp/src/layer_manager.cpp
    cpp/src/color_utils.cpp
)

# Core library
add_library(artflow_core STATIC
    ${CANVAS_SOURCES}
    ${BRUSH_SOURCES}
    ${LAYER_SOURCES}
)

target_link_libraries(artflow_core
    ${OPENGL_LIBRARIES}
)

# Python bindings
pybind11_add_module(artflow_engine
    bindings/python_bindings.cpp
)

target_link_libraries(artflow_engine PRIVATE
    artflow_core
)

# Installation
install(TARGETS artflow_core artflow_engine
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)
