class Memory:
    def __init__(self):
        self.chat_memory = {"messages": []}
        self.variables = {}

    def load_memory_variables(self, _):
        return self.variables

    def save_context(self, inputs, outputs):
        self.variables.update(outputs)
        self.chat_memory["messages"].append({"inputs": inputs, "outputs": outputs})

    def clear(self):
        self.variables = {}
        self.chat_memory["messages"] = []

memory = Memory()

class OpportunityMemory:
    def __init__(self):
        self.variables = {}

    def load_memory_variables(self, _):
        return self.variables

    def save_context(self, inputs, outputs):
        self.variables.update(outputs)

    def clear(self):
        self.variables = {}

opportunity_memory = OpportunityMemory()
