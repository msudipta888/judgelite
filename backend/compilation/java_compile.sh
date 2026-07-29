#!/bin/bash
set -u

SRC=/code/Main.java
BIN=/tmp/main
INPUT=/code/input.txt
TIME_LIMIT="${TIME_LIMIT:-5}"
# check if src file exists or not before compiling
if [ ! -f "$SRC" ]; then
   echo "Source file missing" >&2
   exit 2
fi

mkdir -p "$BIN"

# compile the src file
javac -d "$BIN" "$SRC" 2> /tmp/compile_err.txt 

# check if the compilation was successful 
if [ $? -ne 0 ]; then
   echo "COMPILE_ERROR" >&2
   cat /tmp/compile_err.txt >&2
   exit 1
fi

# run the compiled binary with the given input 
timeout "$TIME_LIMIT"s java -cp "$BIN" Main < "$INPUT"
exit $? 