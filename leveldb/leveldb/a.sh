#!/bin/sh
dir=`pwd`
filelist=`find $dir -type f -name "*.c" -or -name "*.h" -or -name "*.cc" -or -name "*.cpp" -or -name "*.hpp"` 

for file in $filelist
do
    echo $file
done