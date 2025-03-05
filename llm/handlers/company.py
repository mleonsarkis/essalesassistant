import logging
import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from data.memory import memory
from utils.loader import load_json
from config.settings import OPENAI_API_KEY

# Configure logging for debugging.
logging.basicConfig(level=logging.INFO)

# Load known companies.
known_companies = load_json("data/known_companies.json")
logging.info(f"Loaded known companies: {known_companies}")

# Initialize the LLM.
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

# Prompt to extract a company name and determine if the user's query is about that company.
extraction_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are an assistant that extracts a company name from the user's message and determines if the user is asking for a company profile.
Extract only the company name and decide if the message is a query about that company.
Output a JSON object with the following format:
{
  "company_name": "<extracted company name, or 'none' if not mentioned>",
  "is_company_query": <true or false>
}
User Input: {user_input}
Output JSON:"""
)

# Create a chain for extracting the company name and query flag.
extraction_chain = LLMChain(llm=llm, prompt=extraction_prompt)

# Prompt for generating an extensive company profile.
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

# Create a chain for generating the company profile.
profile_chain = LLMChain(llm=llm, prompt=profile_prompt)

class CompanyHandler:
    def __init__(self):
        self.extraction_chain = extraction_chain
        self.profile_chain = profile_chain

    async def handle(self, user_input: str) -> str:
        # Use the LLM to extract the company name and whether the query is about the company.
        extraction_result = await self.extraction_chain.arun(user_input=user_input)
        logging.info(f"Extraction result: {extraction_result}")

        try:
            result_json = json.loads(extraction_result)
        except json.JSONDecodeError:
            return "I'm sorry, I couldn't extract the company name. Please rephrase your query."

        candidate = result_json.get("company_name", "").strip().lower()
        is_query = result_json.get("is_company_query", False)

        # If the LLM doesn't think the user is asking about a company, ask for clarification.
        if not is_query or candidate == "none" or not candidate:
            return "It doesn't seem that you're asking about a company's profile. Could you please specify which company you'd like details for?"

        logging.info(f"Extracted candidate company: '{candidate}'")

        # Check if the candidate exists in known companies.
        known_company = next(
            (c for c in known_companies if c["company_name"].lower() == candidate),
            None
        )
        if known_company:
            return (
                f"{known_company['company_name']} is a known company you worked with in the past. "
                f"Project Details: {known_company['project_details']} (Worked with: {known_company['worked_with']}). "
                f"Contacts: {', '.join(known_company['contacts'])}."
            )
        else:
            # Save/update memory with the candidate.
            memory.save_context({"user_message": user_input}, {"current_company": candidate})
            # Generate an extensive profile using the LLM.
            profile = await self.profile_chain.arun(company_name=candidate)
            return profile
