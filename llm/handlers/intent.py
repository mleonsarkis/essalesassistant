from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config.settings import OPENAI_API_KEY
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

intent_prompt = PromptTemplate(
    input_variables=["user_message"],
    template="""
You are an intent classifier. Based on the following user message, return exactly one word that indicates the user's intent.
Your allowed outputs are: "greeting", "goodbye", "thanks", "company_query", "opportunity_creation", or "proposal_draft".

User Message: {user_message}

Answer with exactly one of the allowed words.
"""
)

class IntentClassifier:
    def __init__(self):
        self.chain = LLMChain(llm=llm, prompt=intent_prompt)

    async def classify(self, user_message: str) -> str:
        intent = await self.chain.arun(user_message=user_message)
        intent = intent.strip().lower()
        logging.info(f"Intent classifier returned: {intent}")
        return intent
