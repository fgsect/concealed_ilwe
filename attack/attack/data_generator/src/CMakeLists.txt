# Attack include directory
include_directories(${CMAKE_SOURCE_DIR}/include/attack)

# libnpy include directory
include_directories(${LIBNPY_PATH}/include)

# Data generator
add_executable(data_generator data_generator.cpp)

# Linker
target_link_libraries(data_generator PUBLIC masked_dilithium_lib)
target_link_libraries(data_generator PRIVATE libnpy)
