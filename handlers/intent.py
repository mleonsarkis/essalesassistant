from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config.settings import OPENAI_API_KEY
from utils.loader import parse_response
import logging

logging.basicConfig(level=logging.WARNING)

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
    def __init__(self, llm):
        self.llm = llm
        self.chain = intent_prompt | llm

    async def classify(self, user_message: str) -> str:
        intent = await self.chain.ainvoke({"user_message":user_message})
        intent = parse_response(intent)
        intent = intent.strip().lower()
        logging.info(f"Intent classifier returned: {intent}")
        return intent
