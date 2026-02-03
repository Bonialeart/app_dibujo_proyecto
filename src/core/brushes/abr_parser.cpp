/**
 * ArtFlow Studio - ABR Parser Implementation
 */

#include "abr_parser.h"
#include <fstream>
#include <stdexcept>
#include <cstring>

namespace artflow {

uint16_t ABRParser::readUInt16BE(const uint8_t* data, size_t offset) {
    return (static_cast<uint16_t>(data[offset]) << 8) |
            static_cast<uint16_t>(data[offset + 1]);
}

uint32_t ABRParser::readUInt32BE(const uint8_t* data, size_t offset) {
    return (static_cast<uint32_t>(data[offset]) << 24) |
           (static_cast<uint32_t>(data[offset + 1]) << 16) |
           (static_cast<uint32_t>(data[offset + 2]) << 8) |
            static_cast<uint32_t>(data[offset + 3]);
}

std::string ABRParser::readPascalString(const uint8_t* data, size_t& offset) {
    uint8_t len = data[offset++];
    std::string result(reinterpret_cast<const char*>(&data[offset]), len);
    offset += len;
    if ((len + 1) % 2 != 0) offset++; // Pad to even boundary
    return result;
}

bool ABRParser::isValidABR(const std::string& filePath) {
    std::ifstream file(filePath, std::ios::binary);
    if (!file) return false;
    
    uint8_t header[4];
    file.read(reinterpret_cast<char*>(header), 4);
    
    uint16_t version = readUInt16BE(header, 0);
    return version >= 1 && version <= 10;
}

ABRFile ABRParser::parse(const std::string& filePath) {
    std::ifstream file(filePath, std::ios::binary | std::ios::ate);
    if (!file) {
        throw std::runtime_error("Failed to open ABR file: " + filePath);
    }
    
    size_t size = file.tellg();
    file.seekg(0);
    
    std::vector<uint8_t> data(size);
    file.read(reinterpret_cast<char*>(data.data()), size);
    
    return parseFromMemory(data.data(), size);
}

ABRFile ABRParser::parseFromMemory(const uint8_t* data, size_t size) {
    if (size < 4) {
        throw std::runtime_error("ABR file too small");
    }
    
    uint16_t version = readUInt16BE(data, 0);
    
    ABRFile result;
    result.version = version;
    
    if (version == 1 || version == 2) {
        return parseVersion1(data, size);
    } else if (version >= 6 && version <= 10) {
        return parseVersion6(data, size);
    } else {
        throw std::runtime_error("Unsupported ABR version: " + std::to_string(version));
    }
}

ABRFile ABRParser::parseVersion1(const uint8_t* data, size_t size) {
    ABRFile result;
    result.version = readUInt16BE(data, 0);
    
    uint16_t count = readUInt16BE(data, 2);
    size_t offset = 4;
    
    for (uint16_t i = 0; i < count && offset < size; ++i) {
        uint16_t brushType = readUInt16BE(data, offset);
        uint32_t brushSize = readUInt32BE(data, offset + 2);
        offset += 6;
        
        if (brushType == 2) { // Sampled brush
            ABRBrush brush = parseSampledBrush(data + offset - 6, offset);
            brush.name = "Brush " + std::to_string(i + 1);
            result.brushes.push_back(std::move(brush));
        }
        
        offset += brushSize;
    }
    
    return result;
}

ABRFile ABRParser::parseVersion6(const uint8_t* data, size_t size) {
    ABRFile result;
    result.version = readUInt16BE(data, 0);
    result.subVersion = readUInt16BE(data, 2);
    
    size_t offset = 4;
    
    // Look for 8BIM sections
    while (offset + 12 < size) {
        // Check for 8BIM signature
        if (data[offset] == '8' && data[offset + 1] == 'B' &&
            data[offset + 2] == 'I' && data[offset + 3] == 'M') {
            
            offset += 4;
            
            // Read section key
            char key[5] = {0};
            std::memcpy(key, &data[offset], 4);
            offset += 4;
            
            // Read section size
            uint32_t sectionSize = readUInt32BE(data, offset);
            offset += 4;
            
            if (std::strcmp(key, "samp") == 0) {
                // Parse sampled brushes
                size_t sectionEnd = offset + sectionSize;
                while (offset < sectionEnd && offset < size) {
                    uint32_t brushLen = readUInt32BE(data, offset);
                    if (brushLen == 0) break;
                    offset += 4;
                    
                    if (offset + brushLen > size) break;
                    
                    ABRBrush brush;
                    
                    // Parse brush data
                    size_t brushStart = offset;
                    
                    // Skip misc data, find dimensions
                    brush.diameter = readUInt32BE(data, offset + 4);
                    uint32_t depth = readUInt32BE(data, offset + 8);
                    brush.patternHeight = readUInt32BE(data, offset + 12);
                    brush.patternWidth = readUInt32BE(data, offset + 16);
                    
                    // Read pattern data
                    size_t dataOffset = offset + 28;
                    size_t patternSize = brush.patternWidth * brush.patternHeight;
                    
                    if (dataOffset + patternSize <= size) {
                        brush.pattern.resize(patternSize);
                        std::memcpy(brush.pattern.data(), &data[dataOffset], patternSize);
                    }
                    
                    brush.name = "Brush " + std::to_string(result.brushes.size() + 1);
                    result.brushes.push_back(std::move(brush));
                    
                    offset = brushStart + brushLen;
                }
            } else {
                offset += sectionSize;
            }
            
            // Pad to even boundary
            if (sectionSize % 2 != 0) offset++;
        } else {
            offset++;
        }
    }
    
    return result;
}

ABRBrush ABRParser::parseSampledBrush(const uint8_t* data, size_t& offset) {
    ABRBrush brush;
    
    // Parse brush header
    uint32_t miscSize = readUInt32BE(data, offset);
    offset += 4 + miscSize;
    
    uint16_t spacing = readUInt16BE(data, offset);
    brush.spacing = spacing / 100.0f;
    offset += 2;
    
    uint16_t diameter = readUInt16BE(data, offset);
    brush.diameter = diameter;
    offset += 2;
    
    // Read pattern dimensions
    brush.patternHeight = readUInt32BE(data, offset);
    brush.patternWidth = readUInt32BE(data, offset + 4);
    offset += 8;
    
    // Skip depth info
    offset += 4;
    
    // Read pattern data (RLE compressed or raw)
    size_t patternSize = brush.patternWidth * brush.patternHeight;
    brush.pattern.resize(patternSize);
    
    // Simplified: assume raw data
    std::memcpy(brush.pattern.data(), &data[offset], patternSize);
    offset += patternSize;
    
    return brush;
}

} // namespace artflow
