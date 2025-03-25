from commands.base import IntentCommand

class FallbackCommand(IntentCommand):
    async def execute(self, user_input: str, session_id: str) -> str:
        return "Sorry, I'm just a sales assistant and not trained to answer that."