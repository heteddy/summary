# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.15

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:


#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:


# Remove some rules from gmake that .SUFFIXES does not remove.
SUFFIXES =

.SUFFIXES: .hpux_make_needs_suffix_list


# Suppress display of executed commands.
$(VERBOSE).SILENT:


# A target that is always out of date.
cmake_force:

.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /Applications/CLion.app/Contents/bin/cmake/mac/bin/cmake

# The command to remove a file.
RM = /Applications/CLion.app/Contents/bin/cmake/mac/bin/cmake -E remove -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /Users/hedetao/code/summary/leveldb/leveldb

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug

# Include any dependencies generated for this target.
include CMakeFiles/cache_test.dir/depend.make

# Include the progress variables for this target.
include CMakeFiles/cache_test.dir/progress.make

# Include the compile flags for this target's objects.
include CMakeFiles/cache_test.dir/flags.make

CMakeFiles/cache_test.dir/util/testutil.cc.o: CMakeFiles/cache_test.dir/flags.make
CMakeFiles/cache_test.dir/util/testutil.cc.o: ../util/testutil.cc
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object CMakeFiles/cache_test.dir/util/testutil.cc.o"
	/Library/Developer/CommandLineTools/usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/cache_test.dir/util/testutil.cc.o -c /Users/hedetao/code/summary/leveldb/leveldb/util/testutil.cc

CMakeFiles/cache_test.dir/util/testutil.cc.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/cache_test.dir/util/testutil.cc.i"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /Users/hedetao/code/summary/leveldb/leveldb/util/testutil.cc > CMakeFiles/cache_test.dir/util/testutil.cc.i

CMakeFiles/cache_test.dir/util/testutil.cc.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/cache_test.dir/util/testutil.cc.s"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /Users/hedetao/code/summary/leveldb/leveldb/util/testutil.cc -o CMakeFiles/cache_test.dir/util/testutil.cc.s

CMakeFiles/cache_test.dir/util/cache_test.cc.o: CMakeFiles/cache_test.dir/flags.make
CMakeFiles/cache_test.dir/util/cache_test.cc.o: ../util/cache_test.cc
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Building CXX object CMakeFiles/cache_test.dir/util/cache_test.cc.o"
	/Library/Developer/CommandLineTools/usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/cache_test.dir/util/cache_test.cc.o -c /Users/hedetao/code/summary/leveldb/leveldb/util/cache_test.cc

CMakeFiles/cache_test.dir/util/cache_test.cc.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/cache_test.dir/util/cache_test.cc.i"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /Users/hedetao/code/summary/leveldb/leveldb/util/cache_test.cc > CMakeFiles/cache_test.dir/util/cache_test.cc.i

CMakeFiles/cache_test.dir/util/cache_test.cc.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/cache_test.dir/util/cache_test.cc.s"
	/Library/Developer/CommandLineTools/usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /Users/hedetao/code/summary/leveldb/leveldb/util/cache_test.cc -o CMakeFiles/cache_test.dir/util/cache_test.cc.s

# Object files for target cache_test
cache_test_OBJECTS = \
"CMakeFiles/cache_test.dir/util/testutil.cc.o" \
"CMakeFiles/cache_test.dir/util/cache_test.cc.o"

# External object files for target cache_test
cache_test_EXTERNAL_OBJECTS =

cache_test: CMakeFiles/cache_test.dir/util/testutil.cc.o
cache_test: CMakeFiles/cache_test.dir/util/cache_test.cc.o
cache_test: CMakeFiles/cache_test.dir/build.make
cache_test: libleveldb.a
cache_test: lib/libgmockd.a
cache_test: lib/libgtestd.a
cache_test: third_party/benchmark/src/libbenchmark.a
cache_test: CMakeFiles/cache_test.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug/CMakeFiles --progress-num=$(CMAKE_PROGRESS_3) "Linking CXX executable cache_test"
	$(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/cache_test.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
CMakeFiles/cache_test.dir/build: cache_test

.PHONY : CMakeFiles/cache_test.dir/build

CMakeFiles/cache_test.dir/clean:
	$(CMAKE_COMMAND) -P CMakeFiles/cache_test.dir/cmake_clean.cmake
.PHONY : CMakeFiles/cache_test.dir/clean

CMakeFiles/cache_test.dir/depend:
	cd /Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /Users/hedetao/code/summary/leveldb/leveldb /Users/hedetao/code/summary/leveldb/leveldb /Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug /Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug /Users/hedetao/code/summary/leveldb/leveldb/cmake-build-debug/CMakeFiles/cache_test.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : CMakeFiles/cache_test.dir/depend

