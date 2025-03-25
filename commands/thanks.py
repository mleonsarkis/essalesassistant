from commands.base import IntentCommand

class ThanksCommand(IntentCommand):
    async def execute(self, user_input: str, session_id: str) -> str:
        return "You're welcome! Let me know if you need anything else."