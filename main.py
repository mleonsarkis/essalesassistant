from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Test Azure FastAPI Deployment"}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
