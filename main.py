import os
from fastapi import FastAPI, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from fastapi import FastAPI, Request
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

app = FastAPI()

MICROSOFT_APP_ID = os.environ.get("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.environ.get("MICROSOFT_APP_PASSWORD", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()


llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

# Define Prompt Template for Company Information Retrieval
company_prompt = PromptTemplate(
    input_variables=["company_name"],
    template="Provide a brief company profile for {company_name}, including industry, size, location, revenue, and recent news. If no data is available, say 'No information found.'"
)

company_chain = LLMChain(llm=llm, prompt=company_prompt)


# Define a Function to Handle User Queries
def process_user_query(user_input: str):
    """
    Determines if the query is related to company information.
    If yes, fetches data using LangChain & OpenAI GPT-4.
    Otherwise, returns a default response.
    """
    keywords = ["company", "business", "organization", "firm", "corporation", "enterprise"]

    if any(keyword in user_input.lower() for keyword in keywords):
        # Extract company name (assumes last word is the company name)
        company_name = user_input.split()[-1]
        response = company_chain.run(company_name)
    else:
        response = "Sorry, I'm just a sales assistant and not trained to answer that."

    return response


# Microsoft Teams Endpoint
@app.post("/teams")
async def teams_webhook(request: Request):
    data = await request.json()
    user_message = data.get("text", "")

    if not user_message:
        return {"message": "No user input received."}

    bot_response = process_user_query(user_message)
    return {"message": bot_response}


# Health Check Endpoint
@app.get("/")
def health_check():
    return {"message": "Sales Assistant Bot is running!"}
