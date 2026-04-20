"""Application entrypoint.

Boots the agentic assistant:
  1. Configures structured logging.
  2. Instantiates the LLM and domain handlers.
  3. Builds the tool registry (skills + hooks).
  4. Wraps everything in a `SalesAgent` and hands it to the bot.
"""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from fastapi import FastAPI, Request, Response, status
from langchain_openai import ChatOpenAI

from agent import SalesAgent, build_registry
from bot.bot import MyBot
from config.settings import OPENAI_API_KEY
from handlers.company import CompanyHandler
from handlers.opportunity import OpportunityHandler
from handlers.proposal import ProposalHandler
from observability.logging import configure_logging, get_logger

configure_logging(level=logging.INFO)
_LOG = get_logger("essales.main")

app = FastAPI(title="ES Sales Agentic Assistant")

# Bot Framework credentials (empty strings are fine for local dev).
app_id = os.getenv("MICROSOFT_APP_ID", "")
app_password = os.getenv("MICROSOFT_APP_PASSWORD", "")
adapter = BotFrameworkAdapter(BotFrameworkAdapterSettings(app_id, app_password))

llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=OPENAI_API_KEY)

# Domain handlers (preserved; now called through the skills layer, not the agent).
company_handler = CompanyHandler(llm)
opportunity_handler = OpportunityHandler(llm)
proposal_handler = ProposalHandler(llm)

registry = build_registry(
    opportunity_handler=opportunity_handler,
    company_handler=company_handler,
    proposal_handler=proposal_handler,
)
sales_agent = SalesAgent(llm=llm, registry=registry)
bot = MyBot(sales_agent)


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

    except Exception as exc:  # noqa: BLE001
        _LOG.exception("error handling message: %s", exc)
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "ES Sales Agentic Assistant"}


@app.get("/agent/tools")
def list_tools():
    """Discovery endpoint — MCP-style manifest of available skills."""
    return registry.get_manifest()


async def test_agent():
    """Local REPL for ad-hoc testing."""
    print("Sales Assistant – Local Test Mode. Type 'exit' to quit.\n")
    session_id = "local-session"
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit"}:
            print("Bot: Goodbye")
            break
        try:
            reply = await sales_agent.run(user_input, session_id)
            print(f"Bot: {reply}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"Bot: something went wrong ({exc})\n")


if __name__ == "__main__":
    # For production, serve with uvicorn:
    #   uvicorn main:app --host 0.0.0.0 --port 8000
    # For local smoke-testing, run this file directly:
    asyncio.run(test_agent())
