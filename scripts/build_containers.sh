#!/bin/bash
# Helper script to build Apptainer containers from definition files

set -e

RECIPE_DIR="apptainer_recipes"
OUTPUT_DIR="containers"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Building Apptainer containers..."
echo "================================"

# Build Ollama container
if [ -f "$RECIPE_DIR/ollama.def" ]; then
    echo "Building Ollama container..."
    apptainer build "$OUTPUT_DIR/ollama.sif" "$RECIPE_DIR/ollama.def"
    echo "✓ Ollama container built"
fi

# Build vLLM container
if [ -f "$RECIPE_DIR/vllm.def" ]; then
    echo "Building vLLM container..."
    apptainer build "$OUTPUT_DIR/vllm.sif" "$RECIPE_DIR/vllm.def"
    echo "✓ vLLM container built"
fi

# Build ChromaDB container
if [ -f "$RECIPE_DIR/chromadb.def" ]; then
    echo "Building ChromaDB container..."
    apptainer build "$OUTPUT_DIR/chromadb.sif" "$RECIPE_DIR/chromadb.def"
    echo "✓ ChromaDB container built"
fi

# Build PostgreSQL container
if [ -f "$RECIPE_DIR/postgres.def" ]; then
    echo "Building PostgreSQL container..."
    apptainer build "$OUTPUT_DIR/postgres.sif" "$RECIPE_DIR/postgres.def"
    echo "✓ PostgreSQL container built"
fi

echo "================================"
echo "All containers built successfully!"
echo "Containers are in: $OUTPUT_DIR/"
