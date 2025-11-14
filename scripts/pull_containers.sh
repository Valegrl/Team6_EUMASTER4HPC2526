mkdir -p containers
cd containers
apptainer pull docker://ollama/ollama
apptainer pull docker://vllm/vllm-openai:latest
apptainer pull docker://chromadb/chroma:latest
apptainer pull docker://postgres:16
