from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from langchain_setup.create_sales_agent import create_sales_assistant_agent
from utils.loader import parse_response

class MyBot(ActivityHandler):
    def __init__(self, llm, opportunity_handler, company_handler, proposal_handler):
        super().__init__()
        self.llm = llm
        self.opportunity_handler = opportunity_handler
        self.company_handler = company_handler
        self.proposal_handler = proposal_handler

    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text

        # Extract session ID from conversation context
        try:
            session_id = turn_context.activity.get("conversation", {}).get("id", "0")
        except Exception:
            session_id = turn_context.activity.get("chat_id", "0") or "0"

        # Create LangChain agent for the current session
        agent_executor = await create_sales_assistant_agent(
            llm=self.llm,
            opportunity_handler=self.opportunity_handler,
            company_handler=self.company_handler,
            proposal_handler=self.proposal_handler,
            session_id=session_id
        )

        try:
            # Run the agent on user input
            result = await agent_executor.ainvoke({"input":user_input})
            result = parse_response(result)
        except Exception as e:
            result = "Sorry, something went wrong while processing your message."

        # Respond with the result
        await turn_context.send_activity(MessageFactory.text(result))