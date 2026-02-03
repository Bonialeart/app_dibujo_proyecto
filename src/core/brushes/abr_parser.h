/**
 * ArtFlow Studio - ABR Parser Header
 * Parses Adobe Photoshop brush files (.abr)
 */

#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace artflow {

struct ABRBrush {
    std::string name;
    int diameter = 0;
    float spacing = 0.25f;
    float hardness = 1.0f;
    float angle = 0.0f;
    float roundness = 1.0f;
    std::vector<uint8_t> pattern;   // Grayscale pattern data
    int patternWidth = 0;
    int patternHeight = 0;
};

struct ABRFile {
    int version = 0;
    int subVersion = 0;
    std::vector<ABRBrush> brushes;
};

class ABRParser {
public:
    static ABRFile parse(const std::string& filePath);
    static ABRFile parseFromMemory(const uint8_t* data, size_t size);
    static bool isValidABR(const std::string& filePath);

private:
    static ABRFile parseVersion1(const uint8_t* data, size_t size);
    static ABRFile parseVersion6(const uint8_t* data, size_t size);
    static ABRBrush parseSampledBrush(const uint8_t* data, size_t& offset);
    static std::string readPascalString(const uint8_t* data, size_t& offset);
    static uint16_t readUInt16BE(const uint8_t* data, size_t offset);
    static uint32_t readUInt32BE(const uint8_t* data, size_t offset);
};

} // namespace artflow
