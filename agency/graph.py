from .nodes import pm_node , tester_node, human_node, developer_node, input_collector_node
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .states import AgencyState
from typing_extensions import Literal


workflow = StateGraph(AgencyState)

workflow.add_node("product_manager", pm_node)
workflow.add_node("input_collector", input_collector_node)
workflow.add_node("developer", developer_node)
workflow.add_node("tester",tester_node)
workflow.add_node("human_review",human_node)

workflow.add_edge(START , "product_manager")
workflow.add_edge("product_manager","input_collector")
workflow.add_edge("input_collector","developer")
workflow.add_edge("developer", "tester")

# now for conditional edges 

def router(state: AgencyState) -> Literal["developer", "human_review"]:
    logs = state.get("test_logs", "")
    has_error = any(
        kw in logs
        for kw in ("Error", "error", "FAILED", "failed", "exception", "Exception",
                   "[tester exception]", "exit_code", "npm ERR", "SyntaxError",
                   "ModuleNotFoundError", "ImportError")
    )
    if has_error and state.get("iterations", 0) < 5:
        return "developer"
    return "human_review"


workflow.add_conditional_edges("tester",router)
workflow.add_edge("human_review", END)


# compile with in-memory checkpointer (swap for SqliteSaver/RedisSaver in prod)
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)