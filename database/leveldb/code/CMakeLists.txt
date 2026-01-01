cmake_minimum_required(VERSION 3.15)
project(code)
include_directories("../leveldb/build/include"
        "../leveldb/include")
link_directories("../leveldb")
set(CMAKE_CXX_STANDARD 11)

add_executable(code src/main.cpp)
link_libraries("../leveldb/")