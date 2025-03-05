import re
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from data.memory import memory
from utils.loader import load_json
from config.settings import OPENAI_API_KEY

# Load known companies.
known_companies = load_json("data/known_companies.json")
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

company_prompt = PromptTemplate(
    input_variables=["company_name"],
    template="Provide a brief company profile for {company_name}, including industry, size, location, revenue, and recent news."
)

class CompanyHandler:
    def __init__(self):
        self.chain = LLMChain(llm=llm, prompt=company_prompt)

    async def handle(self, user_input: str) -> str:
        # Use regex to search for known company names (case-insensitive)
        matching_companies = []
        for company in known_companies:
            pattern = r'\b' + re.escape(company["company_name"]) + r'\b'
            if re.search(pattern, user_input, re.IGNORECASE):
                matching_companies.append(company["company_name"])
        matching_companies = list(set(matching_companies))
        
        # Retrieve previously stored company from memory.
        stored_company = memory.load_memory_variables({}).get("current_company")
        
        # Determine which company to use.
        if len(matching_companies) > 1:
            return "I detected multiple companies in your message. Could you please specify which one you are referring to?"
        elif len(matching_companies) == 1:
            company_name = matching_companies[0]
        elif stored_company:
            company_name = stored_company
        else:
            return "Please specify the company you are referring to."
        
        # Save or update the company name in memory.
        memory.save_context({"user_message": user_input}, {"current_company": company_name})
        
        # Check if the company is known.
        known_company = next((c for c in known_companies if c["company_name"].lower() == company_name.lower()), None)
        if known_company:
            return (
                f"{company_name} is a known company you worked with in the past. "
                f"You worked on {known_company['project_details']} from {known_company['worked_with']}. "
                f"Contacts: {', '.join(known_company['contacts'])}."
            )
        else:
            return await self.chain.arun(company_name=company_name)

