import asyncio
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from llm.chatbot import process_user_query

class MyBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text
        try:
            session_id = turn_context.activity.get("conversation").get("id","0")
        except Exception as e:
            try:
                session_id = turn_context.activity.get("chat_id", "0")
            except Exception as e:
                session_id = "0"

        result = await process_user_query(user_input, session_id)
        if isinstance(result, dict):
            message = MessageFactory.text(result.get("text", ""))
            message.attachments = result.get("attachments", [])
            await turn_context.send_activity(message)
        else:
            await turn_context.send_activity(result)
