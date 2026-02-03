/**
 * ArtFlow Studio - Color Utilities
 * Color conversion and manipulation
 */

#pragma once

#include <cstdint>
#include <array>

namespace artflow {

namespace color {

// RGB to HSV conversion
std::array<float, 3> rgbToHsv(uint8_t r, uint8_t g, uint8_t b);

// HSV to RGB conversion
std::array<uint8_t, 3> hsvToRgb(float h, float s, float v);

// RGB to HSL conversion
std::array<float, 3> rgbToHsl(uint8_t r, uint8_t g, uint8_t b);

// HSL to RGB conversion
std::array<uint8_t, 3> hslToRgb(float h, float s, float l);

// Blend two colors with alpha
void alphaBlend(uint8_t* dst, const uint8_t* src, float srcOpacity = 1.0f);

// Premultiply alpha
void premultiplyAlpha(uint8_t* pixel);

// Unpremultiply alpha
void unpremultiplyAlpha(uint8_t* pixel);

// Linear interpolation between colors
void lerpColor(uint8_t* result, const uint8_t* a, const uint8_t* b, float t);

// Get luminance (perceived brightness)
float luminance(uint8_t r, uint8_t g, uint8_t b);

// Desaturate color
void desaturate(uint8_t* pixel, float amount);

} // namespace color

} // namespace artflow
