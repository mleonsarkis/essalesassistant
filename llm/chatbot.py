import asyncio
from llm.handlers.intent import IntentClassifier
from llm.handlers.opportunity import OpportunityHandler
from llm.handlers.company import CompanyHandler
from llm.handlers.proposal import ProposalHandler

intent_classifier = IntentClassifier()
opportunity_handler = OpportunityHandler()
company_handler = CompanyHandler()
proposal_handler = ProposalHandler()

async def process_user_query(user_input: str, session_id="0"):
    intent = await intent_classifier.classify(user_input)
    if intent == "greeting":
        return "Hello! I'm Jordan, an automated sales assistant. I can help you find information about companies, create opportunities in HubSpot or draft project proposals."
    elif intent == "goodbye":
        return "Goodbye! Feel free to reach out anytime."
    elif intent == "thanks":
        return "You're welcome! Let me know if you need anything else."
    elif intent == "opportunity_creation":
        return await opportunity_handler.handle(user_input)
    elif intent == "company_query":
        return await company_handler.handle(user_input, session_id)
    elif intent == "proposal_draft":
        return await proposal_handler.handle(user_input)
    else:
        return "Sorry, I'm just a sales assistant and not trained to answer that."
