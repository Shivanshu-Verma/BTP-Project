#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &

# Record Process ID.
pid=$!

# Pause for Ollama to start up.
sleep 5

echo "🔴 Retrieving Llama 3.2 model..."
ollama pull llama3.2
echo "🟢 Done!"

# Wait for the Ollama process to finish.
wait $pid &

# Start the Python server
python3 server.py