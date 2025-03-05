import asyncio
from llm.handlers.intent_handler import IntentClassifier
from llm.handlers.opportunity_handler import OpportunityHandler
from llm.handlers.company_handler import CompanyHandler

# Instantiate handler classes.
intent_classifier = IntentClassifier()
opportunity_handler = OpportunityHandler()
company_handler = CompanyHandler()

async def process_user_query(user_input: str) -> str:
    # Classify the intent.
    intent = await intent_classifier.classify(user_input)
    if intent == "greeting":
        return "Hello! How can I assist you today?"
    elif intent == "goodbye":
        return "Goodbye! Feel free to reach out anytime."
    elif intent == "thanks":
        return "You're welcome! Let me know if you need anything else."
    elif intent == "opportunity_creation":
        return await opportunity_handler.handle(user_input)
    elif intent == "company_query":
        return await company_handler.handle(user_input)
    else:
        return "Sorry, I'm just a sales assistant and not trained to answer that."
