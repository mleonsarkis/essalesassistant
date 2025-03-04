from langchain.memory import ConversationBufferMemory

# Maintain context using LangChain memory
memory = ConversationBufferMemory(memory_key="chat_history", input_key="user_message")
opportunity_memory = ConversationBufferMemory(memory_key="opportunity_data", input_key="user_message")
