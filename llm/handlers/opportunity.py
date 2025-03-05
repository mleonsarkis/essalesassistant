import logging
import json
import asyncio
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from config.settings import OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

opportunity_prompt = PromptTemplate(
    input_variables=["user_message", "previous_data"],
    template="""
You extract opportunity details from the user's message, considering previously provided context.

Required fields:
- Contact Name
- Company Name
- Deal Stage
- Amount (numeric)
- Close Date (YYYY-MM-DD format)

Previous details: {previous_data}

User Message: {user_message}

Return a JSON object:
{{
  "contact_name": "<value or empty>",
  "company_name": "<value or empty>",
  "deal_stage": "<value or empty>",
  "amount": "<numeric or empty>",
  "close_date": "<YYYY-MM-DD or empty>",
  "missing_fields": ["<list missing fields>"]
}}
"""
)

llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.3)
opportunity_chain = LLMChain(llm=llm, prompt=opportunity_prompt)

class OpportunityHandler:
    def __init__(self):
        self.chain = opportunity_chain
        self.stored_data = {}

    async def handle(self, user_input: str) -> str:
        if "reset opportunity" in user_input.lower():
            self.stored_data = {}
            return "Opportunity creation process has been reset."

        previous_data_str = json.dumps(self.stored_data) if self.stored_data else "None"

        raw_output = await self.chain.arun(user_message=user_input, previous_data=previous_data_str)
        logging.info(f"Raw extraction output: {raw_output}")

        try:
            extracted_data = json.loads(raw_output)
        except json.JSONDecodeError:
            return "There was an issue parsing your input. Please clarify the details again."

        for key, value in extracted_data.items():
            if value and key != "missing_fields":
                self.stored_data[key] = value

        validation_errors = []
        if self.stored_data.get("amount"):
            try:
                self.stored_data["amount"] = float(self.stored_data["amount"])
            except ValueError:
                validation_errors.append("amount doesn't have the correct numeric format")

        if self.stored_data.get("close_date"):
            try:
                datetime.strptime(self.stored_data["close_date"], "%Y-%m-%d")
            except ValueError:
                validation_errors.append("close_date doesn't have the correct YYYY-MM-DD format")

        required_fields = ["contact_name", "company_name", "deal_stage", "amount", "close_date"]
        missing_fields = [field for field in required_fields if not self.stored_data.get(field)] + validation_errors

        if missing_fields:
            return f"Please correct or provide the following: {', '.join(missing_fields)}."

        details = "\n".join([f"{k.title().replace('_', ' ')}: {v}" for k, v in self.stored_data.items()])
        self.stored_data = {}
        return f"Opportunity successfully uploaded to HubSpot CRM!\nDetails:\n{details}"
