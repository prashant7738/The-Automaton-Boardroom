from typing import Annotated, TypedDict, List, Dict

class AgencyState(TypedDict):
    app_idea : str              # Original Prompt
    specification : str         #MD file created By PM
    source_code : Dict[str, str]#Dictionay of {"filename.py":"code content"}
    test_logs : str             #Console logs from last test run
    iterations : int            #count to prevent infinite loop
    approved_by_human : bool    #Human in the loop (flag)
    human_feedback : str        #Feedback from human reviewer
    design_questions : List[Dict]# LLM-identified MCQ decisions: [{id, question, options}, ...]
    design_answers : Dict[str, str]# User-selected answers: {"q1": "chosen option text"}

