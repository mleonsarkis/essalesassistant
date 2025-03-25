from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
from utils.loader import parse_response
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from config.settings import REDIS_URL

def get_opportunity_field_memory(session_id: str):
    return RedisChatMessageHistory(url=REDIS_URL, session_id=f"{session_id}_opportunity")

# Prompt for opportunity creation
opportunity_prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""
You are an assistant for collecting sales opportunity data. 
The user may provide full or partial information. Your job is to extract only the following five fields:

- contact_name
- company_name
- deal_stage
- amount
- close_date

Do NOT ask follow-up questions or guess what the user might want.  
If a field is not mentioned, return the string "missing".

Output a *valid JSON* object with these exact keys, like this:

{{
  "contact_name": "...",
  "company_name": "...",
  "deal_stage": "...",
  "amount": "...",
  "close_date": "..."
}}

User Input: {user_input}

JSON:
"""
)

class OpportunityHandler:
    def __init__(self, llm):
        self.chain = opportunity_prompt | llm

    async def handle(self, user_input: str, session_id: str) -> str:
        history = get_opportunity_field_memory(session_id)

        # Load previous field state from memory
        prior_state = self._get_prior_fields(history)

        # Extract from current input only
        result = await self.chain.ainvoke({"user_input": user_input})

        try:
            new_fields = json.loads(result)
        except Exception:
            return "Sorry, I couldn't understand that. Please rephrase."

        # Merge
        for k, v in new_fields.items():
            if v.lower() != "missing":
                prior_state[k] = v

        # Save back into Redis (as stringified JSON)
        history.add_user_message(user_input)
        history.add_ai_message(json.dumps(prior_state))  # save current state

        # Determine missing fields
        required = ["contact_name", "company_name", "deal_stage", "amount", "close_date"]
        missing = [f for f in required if f not in prior_state or not prior_state[f] or prior_state[f].lower() == "missing"]

        if missing:
            return f"Please provide the following missing fields: {', '.join(missing)}."

        # ✅ All fields ready
        # Optionally clear memory
        history.clear()

        return (
            f"✅ Opportunity created:\n"
            f"- Contact: {prior_state['contact_name']}\n"
            f"- Company: {prior_state['company_name']}\n"
            f"- Deal Stage: {prior_state['deal_stage']}\n"
            f"- Amount: {prior_state['amount']}\n"
            f"- Close Date: {prior_state['close_date']}"
        )

    def _get_prior_fields(self, history) -> dict:
        """Reads the last stored AI message and tries to extract the field state."""
        messages = history.messages
        for msg in reversed(messages):
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                try:
                    return json.loads(msg.content)
                except:
                    continue
        return {}