import os
from fastapi import FastAPI, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from fastapi import FastAPI, Request
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

MICROSOFT_APP_ID = os.environ.get("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = os.environ.get("MICROSOFT_APP_PASSWORD", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

app = FastAPI()

# Initialize OpenAI GPT-4 Model via LangChain
llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=OPENAI_API_KEY, temperature=0.7)

# Define Prompt Templates
intent_prompt = PromptTemplate(
    input_variables=["user_message"],
    template="""
    Classify the user's message intent as one of the following:
    - "greeting" if they are saying hello.
    - "company_query" if they are asking about a company's details.
    - "other" if the message does not fall into the above categories.

    User Message: {user_message}
    Response (Only return one of the labels: greeting, company_query, or other):
    """
)

company_prompt = PromptTemplate(
    input_variables=["company_name"],
    template="Provide a brief company profile for {company_name}, including industry, size, location, revenue, and recent news. If no data is available, say 'No information found.'"
)

# Create LangChain Chains
intent_chain = LLMChain(llm=llm, prompt=intent_prompt)
company_chain = LLMChain(llm=llm, prompt=company_prompt)

# Process User Query Using LLM
def process_user_query(user_input: str):
    """
    Uses LLM to determine intent and respond appropriately.
    - Greeting → Respond with a friendly message.
    - Company Query → Fetch company information.
    - Other → Return a default response.
    """
    intent = intent_chain.run(user_input).strip().lower()

    if intent == "greeting":
        return "Hello! How can I assist you with company information today?"
    elif intent == "company_query":
        return company_chain.run(user_input)
    else:
        return "Sorry, I'm just a sales assistant and not trained to answer that."

# Microsoft Teams Webhook
@app.post("/teams")
async def teams_webhook(request: Request):
    data = await request.json()
    print(data)
    user_message = data.get("text", "")

    if not user_message:
        return {"message": "No user input received."}

    bot_response = "Helloo"#process_user_query(user_message)
    return {"message": bot_response}

# Health Check Endpoint
@app.get("/")
def health_check():
    return {"message": "Sales Assistant Bot is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)

