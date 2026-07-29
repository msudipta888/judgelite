#!/bin/bash

set -e

#Get the directory where script or .sh file located

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building from: $PROJECT_DIR"
echo ""

echo "Building gcc 9 image..."
docker build -t judgelite/gcc:9 "$PROJECT_DIR/images/cpp/"

echo "Building Python 3.8 image..."
docker build -t judgelite/python:3.8 "$PROJECT_DIR/images/python/"

echo ""
echo "All images built successfully!"
echo ""
echo "Images:"
docker images | grep judgelite