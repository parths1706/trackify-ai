from typing import TypedDict, Optional, List, Any, Annotated
import operator

class AgentState(TypedDict):
    user_question: str
    chat_history: Annotated[list, operator.add]        # full history passed in
    intent: Optional[dict]          # Node 1 output
    path: Optional[str]             # "executor" | "multi" | "query_gen"
    generated_pipeline: Optional[dict]
    target_collection: Optional[str]
    raw_db_results: Optional[Any]   # merged results from whichever Node 2 ran
    final_response: Optional[str]
    error_log: Optional[str]
    retry_count: int
    query_status: Optional[str]
    error_message: Optional[str]
    raw_pipeline: Optional[str]
