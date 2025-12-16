# Use the official Ollama image as base
FROM ollama/ollama:latest

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Install Python dependencies
RUN pip3 install --break-system-packages fastapi uvicorn ollama

# Set the working directory
WORKDIR /app

# Copy our files into the container
COPY server.py .
COPY entrypoint.sh .

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose the port we want
EXPOSE 8000

# Run the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]