from fastapi import APIRouter, Request, Response
from botbuilder.schema import Activity
from botbuilder.core import TurnContext
from teams.adapter import adapter
from llm.chatbot import process_user_query, process_opportunity

router = APIRouter()


@router.post("/teams")
async def teams_webhook(request: Request):
    body = await request.json()
    activity = Activity().deserialize(body)

    async def aux_func(turn_context: TurnContext):
        user_message = turn_context.activity.text

        # Check if user is adding an opportunity
        if "opportunity" in user_message.lower() or "hubspot" in user_message.lower():
            bot_response = await process_opportunity(user_message)
        else:
            bot_response = await process_user_query(user_message)

        await turn_context.send_activity(bot_response)

    auth_header = request.headers.get("Authorization", "")
    await adapter.process_activity(activity, auth_header, aux_func)

    return Response(status_code=201)
