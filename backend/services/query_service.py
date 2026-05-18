from database import db
from bson import ObjectId
from datetime import datetime, timezone
import json

def _clean(obj):
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if k != "password"}
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def execute_query(collection: str, pipeline: list) -> dict:
    allowed = ["users", "projects", "timeentries", "tasks", "teams", "clients", "tags", "groups"]
    
    if collection not in allowed:
        return {"error": f"Collection '{collection}' not allowed"}
    
    try:
        pipeline_str = json.dumps(pipeline)
        for blocked in ["$out", "$merge", "$planCacheStats"]:
            if blocked in pipeline_str:
                return {"error": "Operation not allowed"}
        
        
        # Get total count separately (lightweight)
        count_pipeline = [s for s in pipeline if "$limit" not in str(s) and "$skip" not in str(s)]
        count_pipeline.append({"$count": "total"})
        
        coll = getattr(db, collection)
        
        count_result = list(coll.aggregate(count_pipeline, maxTimeMS=5000))
        total = count_result[0]["total"] if count_result else 0
        
        results = list(coll.aggregate(pipeline, maxTimeMS=10000))
        cleaned = _clean(results)
        
        print(f"[DEBUG] execute_query({collection}) → {len(cleaned)}/{total} results")
        
        return {
            "total": total,
            "returned": len(cleaned),
            "data": cleaned
        }
    
    except Exception as e:
        print(f"[ERROR] execute_query failed: {e}")
        return {"error": str(e)}
