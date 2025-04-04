# handlers/company_handler.py

import logging
import json
import re
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.runnables import Runnable
from utils.loader import load_json, parse_response
from config.settings import REDIS_URL

logging.basicConfig(level=logging.WARNING)

known_companies = load_json("data/known_companies.json")
logging.info(f"Loaded known companies: {known_companies}")

extraction_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are an assistant that extracts a company name from a user's message and determines if the query is about that company's profile or changing the current company context.
Return only a valid JSON object with exactly three keys:
  - "company_name": the extracted company name in lowercase (if no company name is mentioned, use \"none\")
  - "is_company_query": true if the user is asking for information about the company, otherwise false
  - "change_company": true if the user explicitly indicates changing the current company context, otherwise false

Do not include any additional text.
User Input: {user_input}
Output JSON:"""
)

profile_prompt = PromptTemplate(
    input_variables=["company_name"],
    template="""
Provide an extensive company profile for {company_name} including:
- Industry
- Company Size
- Location
- Annual Revenue
- Recent News (at least one major news item)

Output the profile in a structured format.
"""
)

conversation_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are a helpful sales assistant providing detailed information about companies."
        "Use the conversation history provided below to answer follow-up questions without requiring the company name again. "
        "If the question isn't company-related, respond: 'Sorry, I'm just a sales assistant and not trained to answer that.'\n\n"
        "Conversation History:\n{chat_history}"
    ),
    HumanMessagePromptTemplate.from_template("{user_input}")
])

def format_text(text: str) -> str:
    return re.sub(r"[_\[\]()~`>#+-=|{}!]", "", text)

def get_memory(session_id: str):
    chat_history = RedisChatMessageHistory(url=REDIS_URL, session_id=session_id)
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=chat_history,
        return_messages=True
    )

class CompanyHandler:
    def __init__(self, llm):
        self.llm = llm
        self.extraction_chain = extraction_prompt | llm
        self.profile_chain = profile_prompt | llm

    async def handle(self, user_input: str, session_id: str) -> str:
        memory = get_memory(session_id)
        conversation_chain: Runnable = conversation_prompt | self.llm.with_config(memory=memory)

        extraction_result = await self.extraction_chain.ainvoke({"user_input":user_input})
        extraction_result = parse_response(extraction_result)
        logging.info(f"Raw extraction result: {extraction_result}")

        try:
            result_json = json.loads(extraction_result)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return "I'm sorry, I couldn't extract the company name properly. Please rephrase."

        candidate = result_json.get("company_name", "none").strip().lower()
        is_query = result_json.get("is_company_query", False)
        change_company = result_json.get("change_company", False)

        logging.info(f"Extracted candidate: '{candidate}', is_company_query: {is_query}, change_company: {change_company}")

        if change_company and candidate != "none":
            memory.clear()
            memory.save_context({"user_message": user_input}, {"current_company": candidate})
            return f"Company context changed to {candidate.title()}."

        if candidate != "none" and is_query:
            memory.save_context({"user_message": user_input}, {"current_company": candidate})
            known_company = next((c for c in known_companies if c["company_name"].lower() == candidate), None)

            if known_company:
                response = (
                    f"{known_company['company_name']} is a known company you worked with previously. "
                    f"Project Details: {known_company['project_details']} (Worked with: {known_company['worked_with']}). "
                    f"Contacts: {', '.join(known_company['contacts'])}."
                )
                return response
            else:
                profile = await self.profile_chain.ainvoke({"company_name":candidate})
                profile = parse_response(profile)
                return format_text(profile)

        response = await conversation_chain.ainvoke({"user_input": user_input})
        response = parse_response(response)
        return format_text(response)