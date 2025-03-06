import asyncio
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from llm.chatbot import process_user_query

class MyBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text
        result = await process_user_query(user_input)
        if isinstance(result, dict):
            message = MessageFactory.text(result.get("text", ""))
            message.attachments = result.get("attachments", [])
            await turn_context.send_activity(message)
        else:
            await turn_context.send_activity(result)
