import uvicorn
from fastapi import FastAPI
from teams.handler import router

app = FastAPI()

app.include_router(router)


@app.get("/")
def health_check():
    return {"message": "Sales Assistant Bot is running!"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
