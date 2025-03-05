import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from data.memory import memory
from utils.loader import load_json
from config.settings import OPENAI_API_KEY

# Load known companies.
known_companies = load_json("data/known_companies.json")

# Initialize the LLM.
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

# Extraction prompt: extract company name and determine if the query is about that company.
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

extraction_chain = LLMChain(llm=llm, prompt=extraction_prompt)

# Profile prompt: generate an extensive company profile.
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

class CompanyHandler:
    def __init__(self):
        self.extraction_chain = extraction_chain
        self.profile_chain = profile_chain

    async def handle(self, user_input: str) -> str:
        # Use the LLM to extract company details.
        extraction_result = await self.extraction_chain.arun(user_input=user_input)
    
        
        # Fallback if nothing is returned.
        if not extraction_result or extraction_result.strip() == "":
            return "I'm sorry, I couldn't extract a company name from your input. Could you please rephrase?"
        
        try:
            result_json = json.loads(extraction_result)
        except json.JSONDecodeError as e:

            return "I'm sorry, I couldn't extract the company name properly. Please rephrase your query."

        candidate = result_json.get("company_name", "").strip().lower()
        is_query = result_json.get("is_company_query", False)

        # If the LLM doesn't consider it a company query or no valid company is extracted, ask for clarification.
        if not is_query or candidate == "none" or not candidate:
            return "It doesn't seem like you're asking for a company's profile. Could you please specify which company you'd like details for?"

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
            # Save/update the current company in memory.
            memory.save_context({"user_message": user_input}, {"current_company": candidate})
            # Generate an extensive company profile using the LLM.
            profile = await self.profile_chain.arun(company_name=candidate)
            return profile
