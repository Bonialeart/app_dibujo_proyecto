# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "Debug")
  file(REMOVE_RECURSE
  "ArtFlowStudio_autogen"
  "CMakeFiles\\ArtFlowStudio_autogen.dir\\AutogenUsed.txt"
  "CMakeFiles\\ArtFlowStudio_autogen.dir\\ParseCache.txt"
  )
endif()
