# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import uvicorn

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

@app.post("/")
async def generate(request: PromptRequest):
    try:
        # Call the local Ollama instance
        response = ollama.chat(model='llama3.2', messages=[
            {
                'role': 'user',
                'content': request.prompt,
            },
        ])
        return {"response": response['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Listen on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)