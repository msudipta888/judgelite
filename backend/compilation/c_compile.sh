#!/bin/bash
set -u

SRC=/code/main.c
BIN=/tmp/main
INPUT=/code/input.txt
TIME_LIMIT="${TIME_LIMIT:-5}"
# check if src file exists or not before compiling
if [ ! -f "$SRC" ]; then
   echo "Source file missing" >&2
   exit 2
fi

# compile the src file
gcc -O2 -std=c17 -o "$BIN" "$SRC" -lm 2> /tmp/compile_err.txt 

# check if the compilation was successful 
if [ $? -ne 0 ]; then
   echo "COMPILE_ERROR" >&2
   cat /tmp/compile_err.txt >&2
   exit 1
fi

# run the compiled binary with the given input 
timeout --signal=KILL "$TIME_LIMIT"s "$BIN" < "$INPUT"
exit $? 