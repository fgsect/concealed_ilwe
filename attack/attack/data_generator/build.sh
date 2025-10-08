#!/bin/bash
rm -rf build
mkdir build
export CC=clang
export CXX=clang++
export CFLAGS="-O3 -Wno-format -Wno-unused-variable -Wno-pointer-sign"
export CXXFLAGS="-std=c++17 -Wall -g -O3 -Wno-format -Wno-unused-variable"
export CMAKE_BUILD_PARALLEL_LEVEL=40
cmake -S . -B build
cmake --build build
