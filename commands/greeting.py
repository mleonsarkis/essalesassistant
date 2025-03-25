from commands.base import IntentCommand

class GreetingCommand(IntentCommand):
    async def execute(self, user_input: str, session_id: str) -> str:
        return (
            "Hello! I'm Jordan, an automated sales assistant. "
            "I can help you find information about companies, "
            "create opportunities in HubSpot or draft project proposals."
        )