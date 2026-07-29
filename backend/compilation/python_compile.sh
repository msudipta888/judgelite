#!/bin/bash
set -u

SRC=/code/main.py
INPUT=/code/input.txt
TIME_LIMIT="${TIME_LIMIT:-5}"
# check if src file exists  or not before compiling
if [ ! -f "$SRC" ]; then
   echo "Source file missing" >&2
   exit 2
fi


# check if the compilation was successful 
if [ $? -ne 0 ]; then
   echo "COMPILE_ERROR" >&2
   cat /tmp/compile_err.txt >&2
   exit 1
fi
# check time limits
timeout --signal=KILL "$TIME_LIMIT"s python "$SRC" < "$INPUT"
exit $?  