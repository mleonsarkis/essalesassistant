import uvicorn
from fastapi import FastAPI
import llm.chatbot
import teams.handler
from teams.handler import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def health_check():
    return {"message": "Sales Assistant Bot is running!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
    """
    import asyncio
    async def test_bot():
        print("ES Sales Assistant local test. Type 'exit' to quit.\n")
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print("Goodbye")
                break
            try:
                response = await llm.chatbot.process_user_query(user_input)
                print(f"Bot: {response}\n")
            except Exception as e:
                print(f"Error: {e}\n")
    asyncio.run(test_bot())
    """