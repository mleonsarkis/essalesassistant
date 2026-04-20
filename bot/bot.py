"""Microsoft Bot Framework adapter for the agentic assistant.

The bot is now a thin transport-layer shell: it extracts the session id
and user text from the incoming activity and delegates everything else
to the `SalesAgent`. Intent routing, tool selection, and response
generation happen inside the agent + registry + hooks stack.
"""

from __future__ import annotations

from botbuilder.core import ActivityHandler, MessageFactory, TurnContext

from agent import SalesAgent
from observability.logging import get_logger

_LOG = get_logger("essales.bot")


class MyBot(ActivityHandler):
    def __init__(self, sales_agent: SalesAgent):
        super().__init__()
        self._agent = sales_agent

    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text or ""

        try:
            session_id = turn_context.activity.get("conversation", {}).get("id", "0")
        except Exception:
            session_id = turn_context.activity.get("chat_id", "0") or "0"

        try:
            reply = await self._agent.run(user_input, session_id)
        except Exception as exc:  # noqa: BLE001 — log and degrade gracefully
            _LOG.exception("agent run failed")
            reply = "Sorry, something went wrong while processing your message."

        await turn_context.send_activity(MessageFactory.text(reply))
