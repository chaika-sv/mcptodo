from langgraph.graph import StateGraph
from task_nodes import (
    TaskState,
    priority_node,
    due_date_node,
    category_node,
    assemble_task_node,
    confirmation_node,
)
from llm_provider import AgentConfig, LLMWrapper


def build_graph(config: AgentConfig, tools: list):
    llm = LLMWrapper(config)

    graph = StateGraph(TaskState)

    # Обёртки для асинхронных нод
    async def run_priority(state: TaskState):
        return await priority_node(state, llm)

    async def run_due_date(state: TaskState):
        return await due_date_node(state, llm)

    async def run_category(state: TaskState):
        return await category_node(state, llm)

    # Регистрируем узлы
    graph.add_node("priority", run_priority)
    graph.add_node("due_date", run_due_date)
    graph.add_node("category", run_category)
    graph.add_node("assemble", lambda state: assemble_task_node(state, tools))
    graph.add_node("confirmation", confirmation_node)

    # Связи
    graph.set_entry_point("priority")
    graph.add_edge("priority", "due_date")
    graph.add_edge("due_date", "category")
    graph.add_edge("category", "assemble")
    graph.add_edge("assemble", "confirmation")

    return graph.compile()
