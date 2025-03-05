import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from data.memory import opportunity_memory
from config.settings import OPENAI_API_KEY

# Updated prompt includes previous_data if available.
opportunity_prompt = PromptTemplate(
    input_variables=["user_message", "previous_data"],
    template="""
You are a parser that extracts opportunity details from the user's message.
If some details have been provided earlier, use those as context.
Required fields:
- Contact Name
- Company Name
- Deal Stage
- Amount
- Close Date

Previously provided details (if any): {previous_data}

User Message: {user_message}

Return a valid JSON object with these keys.
For any detail that is missing even after considering the previous data, set its value as an empty string and list that field in "missing_fields".
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

llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)
opportunity_chain = LLMChain(llm=llm, prompt=opportunity_prompt)

class OpportunityHandler:
    def __init__(self):
        self.chain = opportunity_chain

    async def handle(self, user_input: str) -> str:
        # Retrieve stored opportunity data (if any)
        stored_data = opportunity_memory.load_memory_variables({}).get("opportunity_data", {})
        # Convert stored data to a string representation for the prompt
        previous_data_str = "\n".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in stored_data.items()]) if stored_data else "None"

        # Call the chain with both the new message and the previously provided data.
        raw_output = await self.chain.arun(user_message=user_input, previous_data=previous_data_str)
        print("Raw LLM output for opportunity extraction:", raw_output)
        try:
            extracted_data = json.loads(raw_output)
        except json.JSONDecodeError:
            return "Error processing opportunity details. Please try again with a clear message."

        # Merge new details into stored_data (keeping previously provided fields if not updated)
        for key in ["contact_name", "company_name", "deal_stage", "amount", "close_date"]:
            if not stored_data.get(key) and extracted_data.get(key):
                stored_data[key] = extracted_data.get(key)

        missing_fields = extracted_data.get("missing_fields", [])
        if missing_fields:
            # Save updated stored_data into memory
            opportunity_memory.save_context({"user_message": user_input}, {"opportunity_data": stored_data})
            return f"To complete the opportunity, please provide the following missing details: {', '.join(missing_fields)}."

        # Clear the memory to simulate successful submission.
        opportunity_memory.clear()
        details = "\n".join([f"**{k.replace('_', ' ').title()}**: {v}" for k, v in stored_data.items()])
        return f"Opportunity successfully uploaded to HubSpot!\n**Details:**\n{details}"
