import logging
import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.memory import ConversationBufferMemory
from data.memory import memory
from utils.loader import load_json
from config.settings import OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

known_companies = load_json("data/known_companies.json")
logging.info(f"Loaded known companies: {known_companies}")

llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.3)

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

extraction_chain = LLMChain(llm=llm, prompt=extraction_prompt)

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
profile_chain = LLMChain(llm=llm, prompt=profile_prompt)

conversation_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

conversation_prompt = ChatPromptTemplate(
    messages=[
        SystemMessagePromptTemplate.from_template(
            "You are a helpful sales assistant providing detailed information about companies."
            " Use the conversation history provided to answer follow-up questions without requiring the company name again."
            " If the question isn't company-related, respond: 'Sorry, I'm just a sales assistant and not trained to answer that.'"
        ),
        HumanMessagePromptTemplate.from_template("{user_input}"),
    ]
)

conversation_chain = ConversationChain(
    llm=llm,
    memory=conversation_memory,
    prompt=conversation_prompt
)

class CompanyHandler:
    def __init__(self):
        self.extraction_chain = extraction_chain
        self.profile_chain = profile_chain
        self.conversation_chain = conversation_chain

    async def handle(self, user_input: str) -> str:
        extraction_result = await self.extraction_chain.arun(user_input=user_input)
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
            conversation_memory.clear()
            conversation_memory.save_context({"user_message": user_input}, {"current_company": candidate})
            return f"Company context changed to {candidate.title()}."

        if candidate != "none" and is_query:
            conversation_memory.save_context({"user_message": user_input}, {"current_company": candidate})
            known_company = next((c for c in known_companies if c["company_name"].lower() == candidate), None)

            if known_company:
                response = (
                    f"{known_company['company_name']} is a known company you worked with previously. "
                    f"Project Details: {known_company['project_details']} (Worked with: {known_company['worked_with']}). "
                    f"Contacts: {', '.join(known_company['contacts'])}."
                )
                return response
            else:
                profile = await self.profile_chain.arun(company_name=candidate)
                return profile
        else:
            response = await self.conversation_chain.arun(user_input=user_input)
            return response
