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
        body = await request.json()
    else:
        return Response(status_code=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    # Directly await the process_activity call without creating a new loop.
    await adapter.process_activity(activity, auth_header, bot.on_turn)

    return Response(status_code=201)
