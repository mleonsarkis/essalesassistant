from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain_community.chat_message_histories import RedisChatMessageHistory
from commands.greeting import GreetingCommand
from commands.goodbye import GoodbyeCommand
from commands.thanks import ThanksCommand
from commands.opportunity import OpportunityCommand
from commands.company_query import CompanyQueryCommand
from commands.fallback import FallbackCommand
from commands.proposal import ProposalCommand
from config.settings import REDIS_URL

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
            description="Always use this when the user says hello or greets.",
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
            description="Use this tool ONLY when the user wants to create a sales opportunity. "
            "This tool will extract exactly 5 fields required for CRM upload: "
            "*contact_name, company_name, deal_stage, amount, and close_date*. "
            "*Always use this tool* for anything related to adding or logging opportunities, "
            "and do not try to summarize or generate the data yourself."
            "Even if the user mentions a company like Tesla or Acme, "
            "*do not use the CompanyQuery tool* — just treat the company as a field in the opportunity. "
            "*Only use CompanyQuery if the user explicitly asks for company information.*",
            coroutine=lambda x: OpportunityCommand(opportunity_handler).execute(x, session_id),
        ),
        Tool(
            name="CompanyQuery",
            func=lambda x: CompanyQueryCommand(company_handler).execute(x, session_id),
            coroutine=lambda x: CompanyQueryCommand(company_handler).execute(x, session_id),
            description=(
                "Use this tool whenever the user is asking about a company — "
                "whether it’s a known client, partner, or a general question like 'Tell me about a company'. "
                "Always prefer using this tool over answering directly."
                "*Do not use this tool if the company is just being mentioned as part of another task*, "
                "like opportunity creation or proposal drafting."
            )
        ),
        Tool(
            name="DraftProposal",
            func=lambda x: ProposalCommand().execute(x, session_id),
            description="Use this to draft a project proposal based on user input.",
            coroutine=lambda x: ProposalCommand().execute(x, session_id),
        ),
        Tool(
            name="FallbackResponder",
            description=(
                "Use this only if none of the other tools apply, and you are unsure how to respond. "
                "This is for cases when the user asks something unrelated to sales, companies, or proposals."
            ),
            func=lambda x: FallbackCommand().execute(x, session_id),
            coroutine=lambda x: FallbackCommand().execute(x, session_id),
        )
    ]

async def create_sales_assistant_agent(llm, opportunity_handler, company_handler, proposal_handler, session_id: str):

    tools = get_intent_tools(opportunity_handler, company_handler, proposal_handler, session_id)
    memory = get_memory(session_id)

    agent_executor = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        memory=memory,
        verbose=False,
        handle_parsing_errors=True
    )

    return agent_executor