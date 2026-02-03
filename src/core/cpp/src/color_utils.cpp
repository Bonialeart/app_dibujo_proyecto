/**
 * ArtFlow Studio - Color Utilities Implementation
 */

#include "color_utils.h"
#include <algorithm>
#include <cmath>

namespace artflow {
namespace color {

std::array<float, 3> rgbToHsv(uint8_t r, uint8_t g, uint8_t b) {
    float rf = r / 255.0f;
    float gf = g / 255.0f;
    float bf = b / 255.0f;
    
    float maxC = std::max({rf, gf, bf});
    float minC = std::min({rf, gf, bf});
    float delta = maxC - minC;
    
    float h = 0.0f;
    float s = (maxC > 0.0f) ? delta / maxC : 0.0f;
    float v = maxC;
    
    if (delta > 0.0f) {
        if (maxC == rf) {
            h = 60.0f * std::fmod((gf - bf) / delta, 6.0f);
        } else if (maxC == gf) {
            h = 60.0f * ((bf - rf) / delta + 2.0f);
        } else {
            h = 60.0f * ((rf - gf) / delta + 4.0f);
        }
    }
    
    if (h < 0.0f) h += 360.0f;
    
    return {h, s, v};
}

std::array<uint8_t, 3> hsvToRgb(float h, float s, float v) {
    float c = v * s;
    float x = c * (1.0f - std::abs(std::fmod(h / 60.0f, 2.0f) - 1.0f));
    float m = v - c;
    
    float r, g, b;
    if (h < 60.0f)       { r = c; g = x; b = 0; }
    else if (h < 120.0f) { r = x; g = c; b = 0; }
    else if (h < 180.0f) { r = 0; g = c; b = x; }
    else if (h < 240.0f) { r = 0; g = x; b = c; }
    else if (h < 300.0f) { r = x; g = 0; b = c; }
    else                 { r = c; g = 0; b = x; }
    
    return {
        static_cast<uint8_t>((r + m) * 255),
        static_cast<uint8_t>((g + m) * 255),
        static_cast<uint8_t>((b + m) * 255)
    };
}

std::array<float, 3> rgbToHsl(uint8_t r, uint8_t g, uint8_t b) {
    float rf = r / 255.0f;
    float gf = g / 255.0f;
    float bf = b / 255.0f;
    
    float maxC = std::max({rf, gf, bf});
    float minC = std::min({rf, gf, bf});
    float l = (maxC + minC) / 2.0f;
    
    float h = 0.0f;
    float s = 0.0f;
    
    if (maxC != minC) {
        float delta = maxC - minC;
        s = (l > 0.5f) ? delta / (2.0f - maxC - minC) : delta / (maxC + minC);
        
        if (maxC == rf) {
            h = std::fmod((gf - bf) / delta + (gf < bf ? 6.0f : 0.0f), 6.0f);
        } else if (maxC == gf) {
            h = (bf - rf) / delta + 2.0f;
        } else {
            h = (rf - gf) / delta + 4.0f;
        }
        h *= 60.0f;
    }
    
    return {h, s, l};
}

std::array<uint8_t, 3> hslToRgb(float h, float s, float l) {
    if (s == 0.0f) {
        uint8_t v = static_cast<uint8_t>(l * 255);
        return {v, v, v};
    }
    
    auto hueToRgb = [](float p, float q, float t) {
        if (t < 0.0f) t += 1.0f;
        if (t > 1.0f) t -= 1.0f;
        if (t < 1.0f/6.0f) return p + (q - p) * 6.0f * t;
        if (t < 0.5f) return q;
        if (t < 2.0f/3.0f) return p + (q - p) * (2.0f/3.0f - t) * 6.0f;
        return p;
    };
    
    float q = (l < 0.5f) ? l * (1.0f + s) : l + s - l * s;
    float p = 2.0f * l - q;
    float hNorm = h / 360.0f;
    
    return {
        static_cast<uint8_t>(hueToRgb(p, q, hNorm + 1.0f/3.0f) * 255),
        static_cast<uint8_t>(hueToRgb(p, q, hNorm) * 255),
        static_cast<uint8_t>(hueToRgb(p, q, hNorm - 1.0f/3.0f) * 255)
    };
}

void alphaBlend(uint8_t* dst, const uint8_t* src, float srcOpacity) {
    float srcA = (src[3] / 255.0f) * srcOpacity;
    float dstA = dst[3] / 255.0f;
    float outA = srcA + dstA * (1.0f - srcA);
    
    if (outA > 0.0f) {
        dst[0] = static_cast<uint8_t>((src[0] * srcA + dst[0] * dstA * (1.0f - srcA)) / outA);
        dst[1] = static_cast<uint8_t>((src[1] * srcA + dst[1] * dstA * (1.0f - srcA)) / outA);
        dst[2] = static_cast<uint8_t>((src[2] * srcA + dst[2] * dstA * (1.0f - srcA)) / outA);
    }
    dst[3] = static_cast<uint8_t>(outA * 255);
}

void lerpColor(uint8_t* result, const uint8_t* a, const uint8_t* b, float t) {
    result[0] = static_cast<uint8_t>(a[0] + (b[0] - a[0]) * t);
    result[1] = static_cast<uint8_t>(a[1] + (b[1] - a[1]) * t);
    result[2] = static_cast<uint8_t>(a[2] + (b[2] - a[2]) * t);
    result[3] = static_cast<uint8_t>(a[3] + (b[3] - a[3]) * t);
}

float luminance(uint8_t r, uint8_t g, uint8_t b) {
    return 0.2126f * (r / 255.0f) + 0.7152f * (g / 255.0f) + 0.0722f * (b / 255.0f);
}

void desaturate(uint8_t* pixel, float amount) {
    float lum = luminance(pixel[0], pixel[1], pixel[2]);
    uint8_t gray = static_cast<uint8_t>(lum * 255);
    pixel[0] = static_cast<uint8_t>(pixel[0] + (gray - pixel[0]) * amount);
    pixel[1] = static_cast<uint8_t>(pixel[1] + (gray - pixel[1]) * amount);
    pixel[2] = static_cast<uint8_t>(pixel[2] + (gray - pixel[2]) * amount);
}

} // namespace color
} // namespace artflow
