from commands.base import IntentCommand

class OpportunityCommand(IntentCommand):
    def __init__(self, handler):
        self.handler = handler

    async def execute(self, user_input: str, session_id: str) -> str:
        return await self.handler.handle(user_input)