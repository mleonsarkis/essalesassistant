from fastapi import APIRouter, Request, Response
from botbuilder.schema import Activity
from teams.adapter import adapter
from llm.bot import MyBot
import asyncio

router = APIRouter()
bot = MyBot()

@router.post("/teams")
async def teams_webhook(request: Request):
    if "application/json" in request.headers["Content-Type"]:
        body = request.json
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    async def call_bot():
        await adapter.process_activity(activity, auth_header, bot.on_turn)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(call_bot())
    return Response(status=201)
