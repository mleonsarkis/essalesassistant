import asyncio
from botbuilder.core import ActivityHandler, TurnContext
from llm.chatbot import process_user_query

class MyBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text
        response_text = await process_user_query(user_input)
        await turn_context.send_activity(response_text)