from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config.settings import OPENAI_API_KEY

llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

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

class IntentClassifier:
    def __init__(self):
        self.chain = LLMChain(llm=llm, prompt=intent_prompt)

    async def classify(self, user_message: str) -> str:
        intent = await self.chain.arun(user_message=user_message)
        return intent.strip().lower()

