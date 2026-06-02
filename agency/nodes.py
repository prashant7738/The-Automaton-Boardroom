from typing import Annotated , TypedDict, Dict
from typing_extensions import Literal
import os
import json
import re
from dotenv import load_dotenv

from .states import AgencyState

# Load environment variables from .env file
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq



from e2b import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException
from langgraph.types import interrupt

from langsmith import traceable



def model(prompt,temperature = 0.3):

    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            api_key=os.getenv('GROQ_API_KEY')
        )

        return llm.invoke(prompt)
    
    except Exception as e:
        print(f"gemini doesnt get called due to {e}. Now Groq ....")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature = temperature,
            api_key=os.getenv('GOOGLE_API_KEY')
            )
        return llm.invoke(prompt)

       

@traceable
def pm_node(state: AgencyState) -> Dict:
    prompt = f"""You are a Product Manager. Create technical specs for this app idea:
    Idea : {state['app_idea']}
    Provide the required markdown file structures and implementation logic.
    """

    response = model(prompt)

    return{"specification":response.content}


@traceable
def input_collector_node(state: AgencyState) -> Dict:
    prompt = f"""Analyze this app idea and specification. Identify all user inputs needed to run the program.
    App idea: {state['app_idea']}
    Specification: {state['specification']}

    Return ONLY a valid JSON array. Each element must have:
    - "name": Python variable name (snake_case, no spaces)
    - "type": one of int / float / str
    - "description": short human-readable prompt to ask the user

    Example: [{{"name": "num1", "type": "float", "description": "First number"}}, ...]
    If no inputs are needed, return [].
    Return ONLY the JSON array, no markdown, no extra text.
    """

    response = model(prompt, temperature=0.0)
    content = response.content.strip()

    match = re.search(r'\[.*\]', content, re.DOTALL)
    required_inputs = json.loads(match.group()) if match else []

    user_inputs = {}
    if required_inputs:
        user_inputs = interrupt({
            "type": "input_request",
            "inputs": required_inputs,
        })

    return {"required_inputs": required_inputs, "user_inputs": user_inputs}


@traceable
def developer_node(state: AgencyState) -> Dict:
    current_iterations = state.get("iterations",0) + 1

    prompt = f""" You are a Expert Engineer. Write the python code for this specifications
    {state['specification']}

    Previous test failure logs (if any):
    {state['test_logs']}

    STRICT RULES:
    - Return ONLY a single Python file named 'main.py'.
    - ALL logic must be self-contained in that one file. No local imports.
    - Do NOT split code across multiple files or modules.
    - Only use stdlib or third-party pip-installable packages (e.g. requests, flask).
    - Return only the raw Python code, no markdown fences.
    - User provided these input values: {state.get('user_inputs', {})}.
      Use these exact values as variables at the top of the file. Do NOT use input() calls.
      If user_inputs is empty, use reasonable hardcoded defaults.
    """

    response = model(prompt)

    code = response.content
    # Strip markdown code fences if LLM wraps code in ```python ... ```
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first line (```python) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    return {
        "source_code" : {"main.py": code},
        "iterations" : current_iterations
    }


@traceable
def tester_node(state: AgencyState) -> Dict:
    code_to_test = state['source_code']['main.py']
    
    # Ensure code is a string
    if not isinstance(code_to_test, str):
        code_to_test = str(code_to_test)

    with Sandbox.create() as sandbox:
        # Write all files from source_code dict to sandbox
        for filename, content in state['source_code'].items():
            sandbox.files.write(filename, content)

        # Execute it
        try:
            execution = sandbox.commands.run("python main.py")
            # capture stderr(errors) and stdout (print statements)
            logs = execution.stderr if execution.stderr else execution.stdout
            if not logs:
                logs = f"Exit code: {execution.exit_code}. No output captured."
        except CommandExitException as e:
            logs = str(e)

    return {"test_logs" : logs}

@traceable
def human_node(state: AgencyState) -> Dict:
    code = state['source_code'].get('main.py', '')
    logs = state.get('test_logs', '')

    # Pause execution and surface info to the caller
    feedback = interrupt({
        "message": "Review required. Approve or provide rejection reason.",
        "code": code,
        "test_logs": logs,
    })

    # feedback is whatever the caller passes via Command(resume=...)
    approved = str(feedback).strip().lower() in ("yes", "approve", "approved", "y")
    return {
        "approved_by_human": approved,
        "human_feedback": str(feedback),
    }