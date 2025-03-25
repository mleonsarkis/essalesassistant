from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
from utils.loader import parse_response

# Prompt for opportunity creation
opportunity_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are a helpful assistant for creating sales opportunities.
Parse the following user input and return a JSON object with:
- contact_name
- company_name
- deal_stage
- amount
- close_date

If any field is missing, indicate it with the value "missing".

User Input: {user_input}
Output JSON:
"""
)

class OpportunityHandler:
    def __init__(self, llm):
        self.chain = opportunity_prompt | llm

    async def handle(self, user_input: str) -> str:
        result = await self.chain.ainvoke({"user_input":user_input})
        result = parse_response(result)
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            return "I couldn't parse the opportunity details properly. Please try again."

        missing_fields = [k for k, v in data.items() if v.lower() == "missing"]
        if missing_fields:
            return f"Please provide the following missing fields: {', '.join(missing_fields)}."

        return (
            f"Opportunity created in HubSpot CRM for:\n"
            f"- Contact: {data['contact_name']}\n"
            f"- Company: {data['company_name']}\n"
            f"- Deal Stage: {data['deal_stage']}\n"
            f"- Amount: {data['amount']}\n"
            f"- Close Date: {data['close_date']}"
        )