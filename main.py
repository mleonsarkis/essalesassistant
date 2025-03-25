import uvicorn
from fastapi import FastAPI, Request, Response, status
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from langchain_setup.create_sales_agent import create_sales_assistant_agent
from botbuilder.schema import Activity
from bot.bot import MyBot
from config.settings import OPENAI_API_KEY
from handlers.company import CompanyHandler
from handlers.opportunity import OpportunityHandler
from handlers.proposal import ProposalHandler
from langchain_openai import ChatOpenAI
import logging
import asyncio
import os

logging.basicConfig(level=logging.WARNING)
app = FastAPI()

# Load Bot Framework credentials (if using Microsoft Bot Service)
# These can be empty strings for local dev
app_id = os.getenv("MICROSOFT_APP_ID", "")
app_password = os.getenv("MICROSOFT_APP_PASSWORD", "")
adapter_settings = BotFrameworkAdapterSettings(app_id, app_password)
adapter = BotFrameworkAdapter(adapter_settings)

llm = ChatOpenAI(
    temperature=0,
    model="gpt-4o",
    api_key=OPENAI_API_KEY
)

# Instantiate handlers and bot
company_handler = CompanyHandler(llm)
opportunity_handler = OpportunityHandler(llm)
proposal_handler = ProposalHandler(llm)
bot = MyBot(llm, opportunity_handler, company_handler, proposal_handler)

@app.post("/bot")
async def messages(req: Request):
    try:
        body = await req.json()
        activity = Activity().deserialize(body)

        async def call_bot_logic(turn_context: TurnContext):
            await bot.on_turn(turn_context)

        auth_header = req.headers.get("Authorization", "")
        await adapter.process_activity(activity, auth_header, call_bot_logic)
        return Response(status_code=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error handling message: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
def health_check():
    return {"message": "Sales Assistant Bot is running!"}


async def test_bot():
    print("Sales Assistant – Local Test Mode. Type 'exit' to quit.\n")

    # Hardcoded session ID for local testing
    session_id = "local-session"

    # Create the LangChain-powered agent
    agent_executor = await create_sales_assistant_agent(
        llm=llm,
        opportunity_handler=opportunity_handler,
        company_handler=company_handler,
        proposal_handler=proposal_handler,
        session_id=session_id
    )

    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit"}:
            print("Bot: Goodbye 👋")
            break
        try:
            raw_response = await agent_executor.ainvoke({"input":user_input})
            if isinstance(raw_response, dict) and "output" in raw_response:
                bot_reply = raw_response["output"]
            else:
                bot_reply = str(raw_response)

            print(f"Bot: {bot_reply}\n")
        except Exception as e:
            print(f"Bot: Oops! Something went wrong.\nError: {e}\n")

if __name__ == "__main__":
    #uvicorn.run("main:app", host="localhost", port=8000, reload=True)
    asyncio.run(test_bot())
