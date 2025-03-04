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
llm = ChatOpenAI(model_name="gpt-4", openai_api_key=OPENAI_API_KEY, temperature=0.7)

adapter_settings = BotFrameworkAdapterSettings(
    app_id=MICROSOFT_APP_ID,
    app_password=MICROSOFT_APP_PASSWORD
)
adapter = BotFrameworkAdapter(adapter_settings)

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

# Process User Query Using LLM and Respond via Bot Framework
async def process_user_query(turn_context: TurnContext):
    user_input = turn_context.activity.text
    intent = intent_chain.run(user_input).strip().lower()

    if intent == "greeting":
        bot_response = "Hello! How can I assist you with today?"
    elif intent == "company_query":
        bot_response = company_chain.run(user_input)
    else:
        bot_response = "Sorry, I'm just a sales assistant and not trained to answer that"

    await turn_context.send_activity(bot_response)
    
@app.post("/teams")
async def teams_webhook(request: Request):
    body = await request.json()
    activity = Activity().deserialize(body)

    async def aux_func(turn_context: TurnContext):
        await process_user_query(turn_context)

    auth_header = request.headers.get("Authorization", "")
    await adapter.process_activity(activity, auth_header, aux_func)

    return Response(status_code=201)

@app.get("/")
def health_check():
    return {"message": "Sales Assistant Bot is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)

