from commands.base import IntentCommand

class GoodbyeCommand(IntentCommand):
    async def execute(self, user_input: str, session_id: str) -> str:
        return "Goodbye! Feel free to reach out anytime."