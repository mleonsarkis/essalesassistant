import asyncio
from handlers.intent_handler import IntentClassifier
from handlers.opportunity_handler import OpportunityHandler
from handlers.company_handler import CompanyHandler
from handlers.proposal_handler import ProposalHandler

intent_classifier = IntentClassifier()
opportunity_handler = OpportunityHandler()
company_handler = CompanyHandler()
proposal_handler = ProposalHandler()

async def process_user_query(user_input: str) -> str:
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
    elif intent == "proposal_draft":
        return await proposal_handler.handle(user_input)
    else:
        return "Sorry, I'm just a sales assistant and not trained to answer that."

if __name__ == "__main__":
    import sys
    user_input = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    result = asyncio.run(process_user_query(user_input))
    print(result)
