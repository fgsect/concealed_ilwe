cmake_minimum_required(VERSION 3.5)

project(
  ProfilingAttackMaskedDilithium
  VERSION 1.0
  LANGUAGES C CXX)

# Export compile commands
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Check if DILITHIUM_MODE is passed from env
if(DEFINED ENV{DILITHIUM_MODE})
	set(DILITHIUM_MODE $ENV{DILITHIUM_MODE})
else()
	set(DILITHIUM_MODE 2) # fallback default
endif()

# Global compile definitions
add_definitions(-DUSE_GLOP -DMASKING_ORDER=1 -DDILITHIUM_MODE=${DILITHIUM_MODE})

# Attack source directories
add_subdirectory(src)

set(DILITHIUM_PATH ${CMAKE_CURRENT_SOURCE_DIR}/extern/Masked_Dilithium/Dilithium)
set(MASKING_PATH ${CMAKE_CURRENT_SOURCE_DIR}/extern/Masked_Dilithium/Masking)
set(LIBNPY_PATH ${CMAKE_CURRENT_SOURCE_DIR}/extern/libnpy)
set(ATTACK_PATH ${CMAKE_CURRENT_SOURCE_DIR}/src)
# Dilithium2 library
set(FIPS202_SRCS fips202.c symmetric-shake.c)
list(TRANSFORM FIPS202_SRCS PREPEND ${DILITHIUM_PATH}/)
set(DILITHIUM_SRCS packing.c polyvec.c poly.c ntt.c reduce.c rounding.c randombytes.c)
list(TRANSFORM DILITHIUM_SRCS PREPEND ${DILITHIUM_PATH}/)
# Masking
set(MASKING_LIB_SRCS utils.c convtable.c convba_2014.c impconvba.c)
list(TRANSFORM MASKING_LIB_SRCS PREPEND ${MASKING_PATH}/)
set(MASKING_DILITHIUM_SRCS masking_interface.c masked_polyvec_operations.c bench_masked_sign.c)
list(TRANSFORM MASKING_DILITHIUM_SRCS PREPEND ${DILITHIUM_PATH}/)
set(MASKING_SRCS ${MASKING_LIB_SRCS} ${MASKING_DILITHIUM_SRCS})

# Append custom attack source files
set(ATTACK_SRCS sign.c masked_sign.c dilithium_gadgets.c)
list(TRANSFORM ATTACK_SRCS PREPEND ${ATTACK_PATH}/)
list(APPEND DILITHIUM_SRCS ${ATTACK_SRCS})

add_library(masked_dilithium_lib ${DILITHIUM_SRCS} ${MASKING_SRCS})
add_library(fips202_ref ${FIPS202_SRCS})
add_library(libnpy INTERFACE)

target_include_directories(masked_dilithium_lib PUBLIC ${DILITHIUM_PATH})
target_include_directories(masked_dilithium_lib PUBLIC ${MASKING_PATH})
target_include_directories(masked_dilithium_lib PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include/attack) # custom attack headers

target_include_directories(libnpy INTERFACE ${LIBNPY_PATH}/include)

# Linking
target_link_libraries(masked_dilithium_lib INTERFACE fips202_ref)

# Verify build
# set(simpleTest_SRCS ${COMMON_SRCS})
# add_executable(simple_test ${DILITHIUM_PATH}/simple_test.c)
# target_link_libraries(simple_test PUBLIC masked_dilithium_lib)
