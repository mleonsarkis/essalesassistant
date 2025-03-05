import logging
import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from data.memory import memory
from utils.loader import load_json
from config.settings import OPENAI_API_KEY

# Configure logging.
logging.basicConfig(level=logging.INFO)

# Load known companies.
known_companies = load_json("data/known_companies.json")
logging.info(f"Loaded known companies: {known_companies}")

# Initialize the LLM with a lower temperature for more deterministic output.
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.3)

# Extraction prompt: extract a company name and determine if the query is about a company profile.
extraction_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are an assistant that extracts a company name from a user's message and determines if the query is about that company's profile.
Return only a valid JSON object with exactly two keys:
  - "company_name": the extracted company name in lowercase (if no company name is mentioned, use "none")
  - "is_company_query": true if the user is asking for information about the company, otherwise false

Do not include any additional text.
For example, if the input is: "Can you provide information about Intel company?"
Your output should be:
{{"company_name": "intel", "is_company_query": true}}

Now process the following input.
User Input: {user_input}
Output JSON:"""
)

# Create the extraction chain.
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
        try:
            # Call the extraction chain asynchronously.
            extraction_result = await self.extraction_chain.arun(user_input=user_input)
            logging.info(f"Raw extraction result: {extraction_result}")
        except Exception as e:
            logging.error(f"Error during extraction chain call: {e}")
            return "I'm sorry, I couldn't process your request. Could you please rephrase your query?"

        try:
            result_json = json.loads(extraction_result)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return f"I'm sorry, I couldn't extract the company name properly. Received: {extraction_result}"

        candidate = result_json.get("company_name", "").strip().lower()
        is_query = result_json.get("is_company_query", False)
        logging.info(f"Extracted candidate: '{candidate}', is_company_query: {is_query}")

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
            # Save/update memory with the candidate.
            memory.save_context({"user_message": user_input}, {"current_company": candidate})
            try:
                # Generate an extensive company profile using the profile chain.
                profile = await self.profile_chain.arun(company_name=candidate)
                return profile
            except Exception as e:
                logging.error(f"Error during profile chain call: {e}")
                return "I'm sorry, I couldn't generate the company profile. Please try again later."
