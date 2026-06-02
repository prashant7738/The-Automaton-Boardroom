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

def router(state :AgencyState) -> Literal["developer","human_review"]:
    if "Error" in state["test_logs"] and state["iterations"] < 5:
        return "developer"  # Loop back to fix the code!
    return "human_review"


workflow.add_conditional_edges("tester",router)
workflow.add_edge("human_review", END)


# compile with in-memory checkpointer (swap for SqliteSaver/RedisSaver in prod)
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)