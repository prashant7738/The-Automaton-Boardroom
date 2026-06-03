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
                   "[tester exception]", "[test result] failed", "exit_code", "npm ERR", "ERR!",
                   "not found", "command not found", "SyntaxError", "ModuleNotFoundError", "ImportError")
    )
    if has_error and state.get("iterations", 0) < 5:
        return "developer"
    return "human_review"


workflow.add_conditional_edges("tester",router)
workflow.add_edge("human_review", END)


# compile with in-memory checkpointer (swap for SqliteSaver/RedisSaver in prod)
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)


def print_graph():
    """Print the Mermaid diagram source and optionally save a PNG."""
    mermaid_str = app.get_graph().draw_mermaid()
    print("\n=== Agent Graph (Mermaid) ===")
    print(mermaid_str)

    try:
        png_bytes = app.get_graph().draw_mermaid_png()
        out_path = "agency_graph.png"
        with open(out_path, "wb") as f:
            f.write(png_bytes)
        print(f"\n[graph saved → {out_path}]")
    except Exception as e:
        print(f"[PNG export skipped: {e}]")


def get_mermaid_png_bytes() -> bytes:
    """Return the graph PNG bytes generated from the internal Mermaid source.

    Use this in notebooks to avoid writing a file, e.g.:
      from IPython.display import Image, display
      display(Image(get_mermaid_png_bytes()))
    """
    return app.get_graph().draw_mermaid_png()


def display_graph_ipython():
    """Display the graph inline in an IPython/Jupyter environment without saving.

    Falls back to printing a message if IPython display tools aren't available.
    """
    try:
        from IPython.display import Image, display
    except Exception as e:
        print(f"[display_graph_ipython skipped: can't import IPython.display: {e}]")
        return

    try:
        png = get_mermaid_png_bytes()
        display(Image(png))
    except Exception as e:
        print(f"[display_graph_ipython failed: {e}]")


if __name__ == "__main__":
    # When invoked as a script, save the PNG and try to open it with
    # the system viewer (`xdg-open` on Linux). This is optional and
    # will silently skip if not available.
    print_graph()
    try:
        import os, shutil, subprocess

        out_path = "agency_graph.png"
        if os.path.exists(out_path):
            if shutil.which("xdg-open"):
                try:
                    subprocess.run(["xdg-open", out_path], check=False)
                except Exception as e:
                    print(f"[open skipped: {e}]")
            else:
                print(f"[open skipped: no xdg-open found; see {out_path}]")
        else:
            print(f"[no image to open: {out_path} not found]")
    except Exception as e:
        print(f"[post-print open skipped: {e}]")