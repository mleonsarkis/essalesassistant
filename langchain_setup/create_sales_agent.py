from langchain.agents import initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain_community.chat_message_histories import RedisChatMessageHistory
from commands.greeting import GreetingCommand
from commands.goodbye import GoodbyeCommand
from commands.thanks import ThanksCommand
from commands.opportunity import OpportunityCommand
from commands.company_query import CompanyQueryCommand
from commands.proposal import ProposalCommand
from config.settings import OPENAI_API_KEY, REDIS_URL
from handlers.company import CompanyHandler
from handlers.proposal import ProposalHandler
from handlers.opportunity import OpportunityHandler

def get_memory(session_id: str):
    chat_history = RedisChatMessageHistory(
        session_id=session_id,
        url=REDIS_URL
    )
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=chat_history,
        return_messages=True
    )

def get_intent_tools(opportunity_handler, company_handler, proposal_handler, session_id: str):
    return [
        Tool(
            name="GreetUser",
            func=lambda x: GreetingCommand().execute(x, session_id),
            description="Use this when the user says hello or greets.",
            coroutine=lambda x: GreetingCommand().execute(x, session_id),
        ),
        Tool(
            name="SayGoodbye",
            func=lambda x: GoodbyeCommand().execute(x, session_id),
            description="Use this when the user is saying goodbye or ending the conversation.",
            coroutine=lambda x: GoodbyeCommand().execute(x, session_id),
        ),
        Tool(
            name="SayThanks",
            func=lambda x: ThanksCommand().execute(x, session_id),
            description="Use this when the user says thank you or expresses gratitude.",
            coroutine=lambda x: ThanksCommand().execute(x, session_id),
        ),
        Tool(
            name="CreateOpportunity",
            func=lambda x: OpportunityCommand(opportunity_handler).execute(x, session_id),
            description="Use this to create a new sales opportunity based on the user's message.",
            coroutine=lambda x: OpportunityCommand(opportunity_handler).execute(x, session_id),
        ),
        Tool(
            name="CompanyQuery",
            func=lambda x: CompanyQueryCommand(company_handler).execute(x, session_id),
            description="Use this to answer user questions about companies.",
            coroutine=lambda x: CompanyQueryCommand(company_handler).execute(x, session_id),
        ),
        Tool(
            name="DraftProposal",
            func=lambda x: ProposalCommand().execute(x, session_id),
            description="Use this to draft a project proposal based on user input.",
            coroutine=lambda x: ProposalCommand().execute(x, session_id),
        ),
    ]

async def create_sales_assistant_agent(llm, opportunity_handler, company_handler, proposal_handler, session_id: str):

    tools = get_intent_tools(opportunity_handler, company_handler, proposal_handler, session_id)
    memory = get_memory(session_id)

    agent_executor = initialize_agent(
        tools=tools,
        llm=llm,
        agent="chat-conversational-react-description",
        memory=memory,
        verbose=False,
        handle_parsing_errors=True
    )

    return agent_executor