import json
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from data.memory import opportunity_memory
from config.settings import OPENAI_API_KEY

llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

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

class OpportunityHandler:
    def __init__(self):
        self.chain = LLMChain(llm=llm, prompt=opportunity_prompt)

    async def handle(self, user_input: str) -> str:
        # Retrieve any stored opportunity data.
        stored_data = opportunity_memory.load_memory_variables({}).get("opportunity_data", {})

        # Extract details using the LLM chain.
        raw_output = await self.chain.arun(user_message=user_input)
        print("Raw LLM output for opportunity extraction:", raw_output)
        try:
            extracted_data = json.loads(raw_output)
        except json.JSONDecodeError:
            return "Error processing opportunity details. Please try again with a clear message."

        # Update stored data with non-empty fields.
        stored_data.update({k: v for k, v in extracted_data.items() if v and k != "missing_fields"})
        missing_fields = extracted_data.get("missing_fields", [])
        if missing_fields:
            opportunity_memory.save_context({"user_message": user_input}, {"opportunity_data": stored_data})
            return f"To complete the opportunity, please provide the following missing details: {', '.join(missing_fields)}."

        # Simulate submission and clear memory.
        opportunity_memory.clear()
        details = "\n".join([f"**{k.replace('_', ' ').title()}**: {v}" for k, v in stored_data.items()])
        return f"Opportunity successfully uploaded to HubSpot!\n**Details:**\n{details}"

