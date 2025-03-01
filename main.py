import os
from fastapi import FastAPI, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes

app = FastAPI()

MICROSOFT_APP_ID = os.environ.get("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.environ.get("MICROSOFT_APP_PASSWORD", "")

adapter_settings = BotFrameworkAdapterSettings(app_id=MICROSOFT_APP_ID, app_password=MICROSOFT_APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)


async def on_message_activity(turn_context: TurnContext):
    await turn_context.send_activity("Hello")


async def messages(req: Request) -> Response:
    body = await req.json()
    activity = Activity().deserialize(body)

    async def aux_func(turn_context: TurnContext):
        if turn_context.activity.type == ActivityTypes.message:
            await on_message_activity(turn_context)
        else:
            await turn_context.send_activity(f"Received a {turn_context.activity.type} activity.")

    auth_header = req.headers.get("Authorization", "")

    await adapter.process_activity(activity, auth_header, aux_func)
    return Response(status_code=201)


@app.post("/teams")
async def teams_webhook(request: Request):
    return await messages(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3978)
