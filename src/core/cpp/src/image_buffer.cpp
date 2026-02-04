/**
 * ArtFlow Studio - Image Buffer Implementation
 */

#include "image_buffer.h"
#include <cstring>
#include <cmath>
#include <algorithm>

namespace artflow {

ImageBuffer::ImageBuffer(int width, int height)
    : m_width(width), m_height(height) {
    m_data.resize(static_cast<size_t>(width * height * 4), 0);
}

ImageBuffer::~ImageBuffer() = default;

uint8_t* ImageBuffer::pixelAt(int x, int y) {
    if (!isValidCoord(x, y)) return nullptr;
    return &m_data[pixelIndex(x, y)];
}

const uint8_t* ImageBuffer::pixelAt(int x, int y) const {
    if (!isValidCoord(x, y)) return nullptr;
    return &m_data[pixelIndex(x, y)];
}

void ImageBuffer::setPixel(int x, int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    if (!isValidCoord(x, y)) return;
    size_t idx = pixelIndex(x, y);
    m_data[idx + 0] = r;
    m_data[idx + 1] = g;
    m_data[idx + 2] = b;
    m_data[idx + 3] = a;
}

void ImageBuffer::fill(uint8_t r, uint8_t g, uint8_t b, uint8_t a) {
    for (int y = 0; y < m_height; ++y) {
        for (int x = 0; x < m_width; ++x) {
            setPixel(x, y, r, g, b, a);
        }
    }
}

void ImageBuffer::clear() {
    std::memset(m_data.data(), 0, m_data.size());
}

void ImageBuffer::blendPixel(int x, int y, uint8_t r, uint8_t g, uint8_t b, uint8_t a, bool alphaLock, bool isEraser) {
    if (!isValidCoord(x, y)) return;
    
    size_t idx = pixelIndex(x, y);
    uint8_t dstAlphaRaw = m_data[idx + 3];
    if (alphaLock && dstAlphaRaw == 0) return;

    float srcA = a / 255.0f;
    float dstA = dstAlphaRaw / 255.0f;

    if (isEraser) {
        // Subtractive Alpha
        float outA = std::max(0.0f, dstA * (1.0f - srcA));
        m_data[idx + 3] = static_cast<uint8_t>(std::clamp(outA * 255.0f, 0.0f, 255.0f));
        return;
    }

    float outA = srcA + dstA * (1.0f - srcA);

    if (alphaLock) {
        outA = dstA; 
        if (outA <= 0.001f) return;
        srcA = std::min(srcA, outA); 
    }
    
    if (outA > 0.0f) {
        float invSrcA = 1.0f - srcA;
        m_data[idx + 0] = static_cast<uint8_t>(std::clamp((r * srcA + m_data[idx + 0] * dstA * invSrcA) / outA, 0.0f, 255.0f));
        m_data[idx + 1] = static_cast<uint8_t>(std::clamp((g * srcA + m_data[idx + 1] * dstA * invSrcA) / outA, 0.0f, 255.0f));
        m_data[idx + 2] = static_cast<uint8_t>(std::clamp((b * srcA + m_data[idx + 2] * dstA * invSrcA) / outA, 0.0f, 255.0f));
    }
    m_data[idx + 3] = static_cast<uint8_t>(std::clamp(outA * 255.0f, 0.0f, 255.0f));
}

void ImageBuffer::drawCircle(int cx, int cy, float radius, 
                              uint8_t r, uint8_t g, uint8_t b, uint8_t a,
                              float hardness, float grain, bool alphaLock, bool isEraser, const ImageBuffer* mask) {
    int minX = std::max(0, static_cast<int>(cx - radius - 1));
    int maxX = std::min(m_width - 1, static_cast<int>(cx + radius + 1));
    int minY = std::max(0, static_cast<int>(cy - radius - 1));
    int maxY = std::min(m_height - 1, static_cast<int>(cy + radius + 1));
    
    float radiusSq = radius * radius;
    
    for (int py = minY; py <= maxY; ++py) {
        for (int px = minX; px <= maxX; ++px) {
            float dx = px - cx;
            float dy = py - cy;
            float distSq = dx * dx + dy * dy;
            
            if (distSq <= radiusSq) {
                float dist = std::sqrt(distSq);
                float normalizedDist = dist / radius;
                
                // Hardness affects falloff
                float falloff = 1.0f;
                if (normalizedDist > hardness) {
                    falloff = 1.0f - (normalizedDist - hardness) / (1.0f - hardness);
                    falloff = std::clamp(falloff, 0.0f, 1.0f);
                }

                // Grain (Noise) logic - Multi-octave organic texture
                float noise = 1.0f;
                if (grain > 0.001f) {
                    auto getHash = [](float x, float y) {
                        uint32_t h = (static_cast<uint32_t>(x) * 1597334677U) ^ (static_cast<uint32_t>(y) * 3812015801U);
                        h *= 0x85ebca6b; h ^= h >> 13; h *= 0xc2b2ae35;
                        return static_cast<float>(h & 0xFFFF) / 65535.0f;
                    };

                    // Octave 1: Coarse (Paper grain)
                    float n1 = getHash(px / 4.0f, py / 4.0f);
                    // Octave 2: Fine (Pigment/Graphite detail)
                    float n2 = getHash(px / 1.5f, py / 1.5f);
                    
                    float randVal = n1 * 0.7f + n2 * 0.3f;
                    
                    // High-contrast curve for "tooth" feeling
                    float grainVal = (randVal - 0.45f) * 3.0f + 0.5f;
                    grainVal = std::clamp(grainVal, 0.0f, 1.0f);
                    
                    noise = (1.0f - grain) + (grainVal * grain);
                }
                
                uint8_t pixelA = static_cast<uint8_t>(a * falloff * noise);
                
                // Clipping Mask support
                if (mask) {
                    const uint8_t* mP = mask->pixelAt(px, py);
                    if (mP) {
                        pixelA = static_cast<uint8_t>(pixelA * (mP[3] / 255.0f));
                    } else {
                        pixelA = 0;
                    }
                }

                if (pixelA > 0) {
                    blendPixel(px, py, r, g, b, pixelA, alphaLock, isEraser);
                }
            }
        }
    }
}

void ImageBuffer::copyFrom(const ImageBuffer& other) {
    if (m_width != other.m_width || m_height != other.m_height) return;
    std::memcpy(m_data.data(), other.m_data.data(), m_data.size());
}

void ImageBuffer::composite(const ImageBuffer& other, int offsetX, int offsetY, float opacity) {
    for (int sy = 0; sy < other.height(); ++sy) {
        int dy = sy + offsetY;
        if (dy < 0 || dy >= m_height) continue;
        
        for (int sx = 0; sx < other.width(); ++sx) {
            int dx = sx + offsetX;
            if (dx < 0 || dx >= m_width) continue;
            
            const uint8_t* srcPixel = other.pixelAt(sx, sy);
            if (srcPixel && srcPixel[3] > 0) {
                uint8_t effA = static_cast<uint8_t>(srcPixel[3] * opacity);
                blendPixel(dx, dy, srcPixel[0], srcPixel[1], srcPixel[2], effA);
            }
        }
    }
}

void ImageBuffer::drawStrokeTextured(float x1, float y1, float x2, float y2, 
                                    const ImageBuffer& stamp, 
                                    float spacing, float opacity, 
                                    bool rotate, float angle_jitter,
                                    bool is_watercolor,
                                    const ImageBuffer* paper_texture) 
{
    float dx = x2 - x1;
    float dy = y2 - y1;
    float dist = std::sqrt(dx*dx + dy*dy);
    
    if (dist < 0.1f) return;
    
    int steps = std::clamp(static_cast<int>(dist / spacing), 1, 1000);
    
    float stepX = dx / steps;
    float stepY = dy / steps;
    
    int sWidth = stamp.width();
    int sHeight = stamp.height();
    int sHalfX = sWidth / 2;
    int sHalfY = sHeight / 2;

    // Pre-calculate paper texture dims
    int pW = 0, pH = 0;
    if (paper_texture) {
        pW = paper_texture->width();
        pH = paper_texture->height();
    }
    
    for (int i = 0; i <= steps; ++i) {
        float cx = x1 + stepX * i;
        float cy = y1 + stepY * i;
        
        // Jitter? Passed in logic? Assuming handled by caller or simple jitter
        // Implementation detail: Rotation of stamp would require resampling.
        // For V1 performance, we stamp aligned (or handled by rotating coords)
        
        // Loop over stamp pixels
        // Optimization: Bounding box clipping
        int startX = static_cast<int>(cx - sHalfX);
        int startY = static_cast<int>(cy - sHalfY);
        
        for (int sy = 0; sy < sHeight; ++sy) {
            for (int sx = 0; sx < sWidth; ++sx) {
                int destX = startX + sx;
                int destY = startY + sy;
                
                // 1. Boundary Check
                if (!isValidCoord(destX, destY)) continue;
                
                // 2. Get Stamp Source Pixel
                const uint8_t* sPixel = stamp.pixelAt(sx, sy);
                uint8_t sA = sPixel[3];
                if (sA == 0) continue; // optimization
                
                // 3. Global Texture Mapping
                float paperMod = 1.0f;
                if (paper_texture) {
                    // Seamless tiling
                    int px = destX % pW;
                    int py = destY % pH;
                    // Suppose paper is grayscale (R=G=B)
                    const uint8_t* pPixel = paper_texture->pixelAt(px, py);
                    float pVal = pPixel[0] / 255.0f;
                    
                    if (is_watercolor) {
                        paperMod = (1.3f - pVal); // Valley accumulation
                    } else {
                        paperMod = pVal * 1.5f;   // Peak hitting
                    }
                }
                
                // 4. Blend
                // Simple alpha blend for now (replace reading destination for speed if needed, but read is required for mix)
                uint8_t* dPixel = this->pixelAt(destX, destY);
                
                // Source Alpha with modifications
                float finalAlpha = (sA / 255.0f) * opacity * paperMod;
                if (finalAlpha > 1.0f) finalAlpha = 1.0f;
                
                // Standard Source-Over Blending
                // out = src * alpha + dst * (1 - alpha)
                float a = finalAlpha;
                float invA = 1.0f - a;
                
                dPixel[0] = static_cast<uint8_t>(sPixel[0] * a + dPixel[0] * invA);
                dPixel[1] = static_cast<uint8_t>(sPixel[1] * a + dPixel[1] * invA);
                dPixel[2] = static_cast<uint8_t>(sPixel[2] * a + dPixel[2] * invA);
                dPixel[3] = static_cast<uint8_t>(255 * a + dPixel[3] * invA); // Simplified alpha addition
            }
        }
    }
}

std::vector<uint8_t> ImageBuffer::getBytes() const {
    return m_data;
}

std::unique_ptr<ImageBuffer> ImageBuffer::fromBytes(const std::vector<uint8_t>& bytes, int width, int height) {
    auto buffer = std::make_unique<ImageBuffer>(width, height);
    if (bytes.size() == buffer->m_data.size()) {
        std::memcpy(buffer->m_data.data(), bytes.data(), bytes.size());
    }
    return buffer;
}

} // namespace artflow
