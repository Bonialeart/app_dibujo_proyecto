cmake_minimum_required(VERSION 3.16)
project(ArtFlowCore VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Find Python and pybind11
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG QUIET)

# If pybind11 not found via config, try subdirectory
if(NOT pybind11_FOUND)
    # Download pybind11 if not present
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.11.1
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# Core Library Sources
set(CORE_SOURCES
    src/brush_engine.cpp
    src/layer_manager.cpp
    src/color_utils.cpp
    src/image_buffer.cpp
)

set(CORE_HEADERS
    include/brush_engine.h
    include/layer_manager.h
    include/color_utils.h
    include/image_buffer.h
)

# Create static library for core
add_library(artflow_core STATIC ${CORE_SOURCES} ${CORE_HEADERS})
target_include_directories(artflow_core PUBLIC include)

# Create Python module
pybind11_add_module(artflow_native 
    bindings/python_bindings.cpp
)
target_link_libraries(artflow_native PRIVATE artflow_core)

# Installation
install(TARGETS artflow_native LIBRARY DESTINATION .)
