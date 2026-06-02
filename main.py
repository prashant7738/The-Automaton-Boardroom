from dotenv import load_dotenv
load_dotenv()

import uuid
from langgraph.types import Command
from agency.graph import app

def main():
    app_idea = input("What app do you want to build? ").strip()
    if not app_idea:
        app_idea = "Create a python code that adds two numbers"

    initial_state = {
        "app_idea": app_idea,
        "specification": "",
        "source_code": {},
        "test_logs": "",
        "iterations": 0,
        "approved_by_human": False,
        "human_feedback": "",
        "required_inputs": [],
        "user_inputs": {},
    }

    # Each run needs a unique thread_id so the checkpointer can save/resume state
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    print(f"Starting Multi-Agent Workflow...")
    print(f"App Idea: {app_idea}\n")

    # --- First run: executes until interrupt ---
    result = app.invoke(initial_state, config)

    # Loop to handle interrupt + optional re-rejection cycle
    while True:
        # Check if execution is paused at an interrupt
        state_snapshot = app.get_state(config)

        if not state_snapshot.next:  # no pending node → workflow finished
            break

        # Surface info collected by interrupt()
        pending = state_snapshot.tasks
        for task in pending:
            if hasattr(task, 'interrupts') and task.interrupts:
                interrupt_payload = task.interrupts[0].value

                if interrupt_payload.get("type") == "input_request":
                    # --- Input collection phase ---
                    print("\n" + "="*60)
                    print("INPUT REQUIRED")
                    print("="*60)
                    answers = {}
                    for inp in interrupt_payload["inputs"]:
                        val = input(f"{inp['description']} ({inp['type']}): ").strip()
                        answers[inp["name"]] = val
                    result = app.invoke(Command(resume=answers), config)

                else:
                    # --- Human review phase ---
                    print("\n" + "="*60)
                    print("HUMAN REVIEW REQUIRED")
                    print("="*60)
                    print("\n--- Generated Code ---")
                    print(interrupt_payload.get("code", ""))
                    print("\n--- Test Logs ---")
                    print(interrupt_payload.get("test_logs", ""))
                    print("="*60)

                    feedback = input("\nApprove? (yes / reason for rejection): ").strip()
                    result = app.invoke(Command(resume=feedback), config)

    print("\nWorkflow completed!")
    final = app.get_state(config).values
    print(f"\nApproved by Human: {final.get('approved_by_human', False)}")
    print(f"\nGenerated Code:\n{final['source_code'].get('main.py', 'N/A')}")
    print(f"\nTest Logs:\n{final.get('test_logs', 'N/A')}")


if __name__ == "__main__":
    main()
