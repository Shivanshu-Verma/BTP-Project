## Build the Docker image

```bash
docker build -t my-llama-server .
```

## Run the container

### GPU (NVIDIA)

Requirements:

- NVIDIA GPU + drivers
- NVIDIA Container Toolkit installed

```bash
docker run -d --gpus=all -p 8000:8000 --name llama-web my-llama-server
```

### CPU-only

```bash
docker run -d -p 8000:8000 --name llama-web my-llama-server
```

### Verify

```bash
docker ps
```

Then open: `http://localhost:8000/`
