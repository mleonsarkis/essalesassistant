import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from utils.loader import load_json
from data.memory import opportunity_memory, memory
from config.settings import OPENAI_API_KEY


known_companies = load_json("data/known_companies.json")

# Initialize OpenAI GPT-4 Model
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

# Prompt to identify opportunity details in user input
opportunity_prompt = PromptTemplate(
    input_variables=["user_message"],
    template="""
    Extract opportunity details from the user's message:
    Required fields:
    - Contact Name
    - Company Name
    - Deal Stage
    - Amount
    - Close Date

    If any information is missing, return a list of missing fields.
    User Message: {user_message}
    Response (JSON format): {"contact_name": "...", "company_name": "...", "deal_stage": "...", "amount": "...", "close_date": "...", "missing_fields": ["..."]}
    """
)

company_prompt = PromptTemplate(
    input_variables=["company_name"],
    template="Provide a brief company profile for {company_name}, including industry, size, location, revenue, and recent news."
)

opportunity_chain = LLMChain(llm=llm, prompt=opportunity_prompt)
company_chain = LLMChain(llm=llm, prompt=company_prompt)


async def process_opportunity(user_input: str):
    """
    Handles the process of creating an opportunity.
    - Checks for missing details.
    - Stores partial data using memory.
    - Mocks HubSpot API submission.
    """
    # Retrieve stored opportunity data
    stored_data = opportunity_memory.load_memory_variables({}).get("opportunity_data", {})

    # Extract opportunity details from user input
    extracted_data = await opportunity_chain.arun(user_message=user_input)
    extracted_data = json.loads(extracted_data)  # Convert JSON response

    # Update stored data
    stored_data.update({k: v for k, v in extracted_data.items() if v and k != "missing_fields"})

    # Check for missing fields
    missing_fields = extracted_data.get("missing_fields", [])
    if missing_fields:
        opportunity_memory.save_context({"user_message": user_input}, {"opportunity_data": stored_data})
        return f"To complete the opportunity, please provide the following missing details: {', '.join(missing_fields)}."

    # Mock HubSpot API submission
    opportunity_memory.clear()
    return f"Opportunity successfully uploaded to HubSpot!\n**Details:**\n" + "\n".join([f"**{k.replace('_', ' ').title()}**: {v}" for k, v in stored_data.items()])


async def process_user_query(user_input: str):
    """
    Determines user intent and fetches the appropriate response.
    """
    # Retrieve conversation context
    memory.load_memory_variables({})

    intent = await company_chain.arun(messages=[HumanMessage(content=user_input)])
    intent = intent.strip().casefold()

    # Handle greetings, goodbyes, and thanks
    if intent == "greeting":
        return "Hello! How can I assist you with company information today?"
    elif intent == "goodbye":
        return "Goodbye! Feel free to reach out anytime."
    elif intent == "thanks":
        return "You're welcome! Let me know if you need anything else."

    # Handle company-related queries with memory support
    chat_history = memory.chat_memory.messages
    previous_company = None
    for msg in reversed(chat_history):
        if "company_query" in msg.content:
            previous_company = msg.content.split(":")[-1].strip()
            break

    if intent == "company_query":
        # Extract company name from user input
        company_name = user_input.split()[-1] if not previous_company else previous_company

        # Check if it's a known company
        known_company = next((c for c in known_companies if c["company_name"].lower() == company_name.lower()), None)

        if known_company:
            return f"{company_name} is a known company you worked with in the past. You worked on {known_company['project_details']} from {known_company['worked_with']}. Contacts: {', '.join(known_company['contacts'])}."

        return await company_chain.arun(company_name=company_name)

    return "Sorry, I'm just a sales assistant and not trained to answer that."
