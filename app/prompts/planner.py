# app/prompts/planner.py
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM = """You are a senior technical project planner.

Produce a detailed task graph. Each task must specify assignee: frontend_coder | backend_coder | db_coder.

Order by dependency: DB tasks first, then backend, then frontend.

## STRICT OUTPUT RULES:
- Return ONLY raw JSON — no markdown, no ```json, no ``` fences
- No triple quotes anywhere
- No explanation text before or after JSON
- JSON must be complete and valid
- ALL keys must be present: task_graph

## Output format:
{{"task_graph":[{{"id":"task_001","name":"str","description":"str --- detailed enough to implement without questions","assignee":"str","depends_on":["task_id"],"expected_files":["path"]}}]}}"""

planner_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        MessagesPlaceholder(variable_name="chat_history"),
        (
            "human",
            "Stack: {stack_json}\nTasks from orchestrator: {tasks_list}\nPRD: {prd_content}",
        ),
    ]
)