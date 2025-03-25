from abc import ABC, abstractmethod

class IntentCommand(ABC):
    @abstractmethod
    async def execute(self, user_input: str, session_id: str) -> str:
        pass