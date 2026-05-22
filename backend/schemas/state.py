from typing import TypedDict, Optional, List, Any

class AgentState(TypedDict):
    user_question: str
    chat_history: List[dict]
    generated_pipeline: Optional[dict]
    target_collection: Optional[str]
    raw_db_results: Optional[Any]
    final_response: Optional[str]
    error_log: Optional[str]
    retry_count: int
