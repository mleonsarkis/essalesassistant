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

# Updated prompt for extracting opportunity details
opportunity_prompt = PromptTemplate(
    input_variables=["user_message"],
    template="""
You are a parser that extracts opportunity details from the user's message.
Extract the following details exactly:
- contact_name
- company_name
- deal_stage
- amount
- close_date

Return a valid JSON object with these keys. 
If any detail is missing, set its value as an empty string and include that field in a "missing_fields" list.
User Message: {user_message}
Output JSON: 
{{
  "contact_name": "<value or empty>",
  "company_name": "<value or empty>",
  "deal_stage": "<value or empty>",
  "amount": "<value or empty>",
  "close_date": "<value or empty>",
  "missing_fields": ["<list any missing field names>"]
}}
"""
)
)

# Prompt for company information (used only when a company query is detected)
company_prompt = PromptTemplate(
    input_variables=["company_name"],
    template="Provide a brief company profile for {company_name}, including industry, size, location, revenue, and recent news."
)

# New prompt for intent classification
intent_prompt = PromptTemplate(
    input_variables=["user_message"],
    template="""
You are a classifier that determines the intent of the user's message.
Possible intents:
- greeting
- goodbye
- thanks
- company_query
- opportunity_creation

If none of the above apply, return "unknown".

User Message: {user_message}
Return only the intent word.
"""
)

# Define the chains
opportunity_chain = LLMChain(llm=llm, prompt=opportunity_prompt)
company_chain = LLMChain(llm=llm, prompt=company_prompt)
intent_chain = LLMChain(llm=llm, prompt=intent_prompt)

async def process_opportunity(user_input: str):
    """
    Handles the process of creating an opportunity:
    - Extracts opportunity details.
    - Checks for missing fields.
    - Stores partial data.
    - Mocks HubSpot API submission.
    """
    # Retrieve stored opportunity data if any
    stored_data = opportunity_memory.load_memory_variables({}).get("opportunity_data", {})

    # Extract opportunity details from user input
    raw_output = await opportunity_chain.arun(user_message=user_input)
    print("Raw LLM output for opportunity extraction:", raw_output)  # Debug log
    try:
        extracted_data = json.loads(raw_output)
    except json.JSONDecodeError:
        return "Error processing opportunity details. Please try again with a clear message."

    # Update stored data with non-empty fields (ignoring missing_fields)
    stored_data.update({k: v for k, v in extracted_data.items() if v and k != "missing_fields"})

    # Check for missing fields
    missing_fields = extracted_data.get("missing_fields", [])
    if missing_fields:
        opportunity_memory.save_context({"user_message": user_input}, {"opportunity_data": stored_data})
        return f"To complete the opportunity, please provide the following missing details: {', '.join(missing_fields)}."

    # Clear memory and simulate API submission
    opportunity_memory.clear()
    details = "\n".join([f"**{k.replace('_', ' ').title()}**: {v}" for k, v in stored_data.items()])
    return f"Opportunity successfully uploaded to HubSpot!\n**Details:**\n{details}"

async def process_user_query(user_input: str):
    """
    Determines the user's intent and fetches the appropriate response.
    """
    # Load conversation context
    memory.load_memory_variables({})

    # Classify the user intent
    intent = await intent_chain.arun(user_message=user_input)
    intent = intent.strip().lower()

    if intent == "greeting":
        return "Hello! How can I assist you today?"
    elif intent == "goodbye":
        return "Goodbye! Feel free to reach out anytime."
    elif intent == "thanks":
        return "You're welcome! Let me know if you need anything else."
    elif intent == "opportunity_creation":
        return await process_opportunity(user_input)
    elif intent == "company_query":
    # Look for known companies mentioned in the user input.
    matching_companies = []
    for company in known_companies:
        if company["company_name"].lower() in user_input.lower():
            matching_companies.append(company["company_name"])
    
    # Remove duplicates.
    matching_companies = list(set(matching_companies))
    
    # Retrieve a previously stored company from memory if available.
    stored_company = memory.load_memory_variables({}).get("current_company")
    
    # Determine which company to use:
    if len(matching_companies) > 1:
        # Ambiguous input: More than one company mentioned.
        return "I detected multiple companies in your message. Could you please specify which one you are referring to?"
    elif len(matching_companies) == 1:
        company_name = matching_companies[0]
    elif stored_company:
        company_name = stored_company
    else:
        # No clear company was provided.
        return "Please specify the company you are referring to."
    
    # Save or update the company name in memory for subsequent queries.
    memory.save_context({"user_message": user_input}, {"current_company": company_name})
    
    # Check if the company is known.
    known_company = next(
        (c for c in known_companies if c["company_name"].lower() == company_name.lower()), 
        None
    )
    if known_company:
        return (
            f"{company_name} is a known company you worked with in the past. "
            f"You worked on {known_company['project_details']} from {known_company['worked_with']}. "
            f"Contacts: {', '.join(known_company['contacts'])}."
        )
    else:
        # Generate a company profile using the company chain.
        return await company_chain.arun(company_name=company_name)
    else:
        return "Sorry, I'm just a sales assistant and not trained to answer that."
