from typing import Annotated, TypedDict, List, Dict

class AgencyState(TypedDict):
    app_idea : str              # Original Prompt
    specification : str         #MD file created By PM
    source_code : Dict[str, str]#Dictionay of {"filename.py":"code content"}
    test_logs : str             #Console logs from last test run
    iterations : int            #count to prevent infinite loop
    approved_by_human : bool    #Human in the loop (flag)
    human_feedback : str        #Feedback from human reviewer
    required_inputs : List[Dict]# LLM-identified inputs: [{name, type, description}, ...]
    user_inputs : Dict[str, str]# User-provided values: {"num1": "5", "num2": "3"}

