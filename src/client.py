

api_address = "http://localhost:11434/api/chat"

ollama_msg = f"curl {api_address} " + """-d '{
  "model": "gemma3",
  "messages": [{
    "role": "user",
    "content": "Hello there!"
  }],
  "stream": false
}'"""




