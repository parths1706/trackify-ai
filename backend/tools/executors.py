from database import db
from bson import ObjectId
import re
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_user(name: str):
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    matches = list(db.users.find({"name": pattern}))
    
    scored_matches = []
    for u in matches:
        score = 0
        u_name = u.get("name", "")
        
        # Match type scoring
        if u_name.lower() == name.lower():
            score += 100
        elif re.search(r"\b" + re.escape(name) + r"\b", u_name, re.IGNORECASE):
            score += 50
        else:
            score += 10
            
        # Status scoring
        if u.get("isActive") is True:
            score += 200
        if u.get("archived") is not True:
            score += 100
            
        scored_matches.append((score, u))
        
    if not scored_matches:
        return None, None, None, f"User '{name}' not found"
        
    scored_matches.sort(key=lambda x: x[0], reverse=True)
    best_user = scored_matches[0][1]
    return best_user["_id"], best_user["name"], best_user.get("email"), None





def resolve_project(name: str):
    project = db.projects.find_one({
        "$and": [
            {"name": {"$regex": name, "$options": "i"}},
            {"name": {"$not": re.compile("^_INX-")}}
        ]
    })
    if not project:
        return None, None, f"Project '{name}' not found"
    return project["_id"], project["name"], None


def parse_date(date_str: str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def build_date_filter(start_date, end_date):
    f = {}
    if start_date:
        sd = parse_date(start_date)
        if sd:
            f["$gte"] = sd
    if end_date:
        ed = parse_date(end_date)
        if ed:
            f["$lte"] = ed
    if f:
        return {"entryDate": f}
    return {}


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------

def get_user_hours(user_name: str, start_date: str = None, end_date: str = None) -> dict:
    try:
        user_id, resolved_name, _, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        match_stage = {"userId": user_id}
        date_filter = build_date_filter(start_date, end_date)
        if date_filter:
            match_stage.update(date_filter)
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None, 
                "total_duration": {"$sum": "$duration"}, 
                "count": {"$sum": 1}
            }}
        ]
        
        res = list(db.timeentries.aggregate(pipeline))
        if not res or res == []:
            return {"status": "no_data", "message": "No records found for this query."}
        total_seconds = res[0].get("total_duration", 0) if res else 0
        entry_count = res[0].get("count", 0) if res else 0
        total_hours = round(total_seconds / 3600, 2)
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "user": resolved_name,
            "total_hours": total_hours,
            "entry_count": entry_count,
            "period": period
        }
    except Exception as e:
        return {"error": f"get_user_hours failed: {str(e)}"}


def get_user_projects(user_name: str, include_archived: bool = False) -> dict:
    try:
        user_id, resolved_name, _, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        query = {"members": user_id, "name": {"$not": re.compile("^_INX-")}}
        if not include_archived:
            query["archived"] = {"$ne": True}
            
        cursor = db.projects.find(query, {"name": 1, "billable": 1, "archived": 1, "_id": 0})
        projects_list = list(cursor)
        if not projects_list or projects_list == []:
            return {"status": "no_data", "message": "No records found for this query."}
        
        return {
            "user": resolved_name,
            "projects": projects_list,
            "count": len(projects_list)
        }
    except Exception as e:
        return {"error": f"get_user_projects failed: {str(e)}"}


def get_project_contributors(project_name: str, start_date: str = None, end_date: str = None, limit=10) -> dict:
    try:
        limit = int(limit)
        project_id, resolved_name, err = resolve_project(project_name)
        if err:
            return {"error": err}
            
        match_stage = {"projectId": project_id}
        date_filter = build_date_filter(start_date, end_date)
        if date_filter:
            match_stage.update(date_filter)
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$userId", "total_duration": {"$sum": "$duration"}}},
            {"$lookup": {
                "from": "users", 
                "localField": "_id", 
                "foreignField": "_id", 
                "as": "user_info"
            }},
            {"$project": {
                "_id": 0,
                "name": {"$arrayElemAt": ["$user_info.name", 0]},
                "total_duration": 1
            }},
            {"$sort": {"total_duration": -1}},
            {"$limit": limit}
        ]
        
        res = list(db.timeentries.aggregate(pipeline))
        if not res or res == []:
            return {"status": "no_data", "message": "No records found for this query."}
        contributors = [
            {"name": item.get("name") or "Unknown", "hours": round(item.get("total_duration", 0) / 3600, 2)}
            for item in res
        ]
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "project": resolved_name,
            "contributors": contributors,
            "period": period
        }
    except Exception as e:
        return {"error": f"get_project_contributors failed: {str(e)}"}


def get_active_employees(start_date: str = None, end_date: str = None, limit=10) -> dict:
    try:
        limit = int(limit)
        match_stage = {"userId": {"$ne": None}}
        date_filter = build_date_filter(start_date, end_date)
        if date_filter:
            match_stage.update(date_filter)

        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$userId", "total_duration": {"$sum": "$duration"}}},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$project": {
                "_id": 0,
                "name": {"$arrayElemAt": ["$user_info.name", 0]},
                "total_duration": 1
            }},
            {"$match": {"name": {"$ne": None}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": limit}
        ]

        res = list(db.timeentries.aggregate(pipeline))
        if not res or res == []:
            return {"status": "no_data", "message": "No records found for this query."}
        employees = [
            {"name": item.get("name", "Unknown"), "hours": round(item.get("total_duration", 0) / 3600, 2)}
            for item in res
        ]

        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)

        return {"employees": employees, "period": period}
    except Exception as e:
        return {"error": f"get_active_employees failed: {str(e)}"}


def get_project_stats(project_name: str, start_date: str = None, end_date: str = None) -> dict:
    try:
        project_id, resolved_name, err = resolve_project(project_name)
        if err:
            return {"error": err}
            
        project_doc = db.projects.find_one({"_id": project_id})
        billable = project_doc.get("billable", False) if project_doc else False
        archived = project_doc.get("archived", False) if project_doc else False
        member_count = len(project_doc.get("members", [])) if project_doc else 0
        
        match_stage = {"projectId": project_id}
        date_filter = build_date_filter(start_date, end_date)
        if date_filter:
            match_stage.update(date_filter)
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": None,
                "total_duration": {"$sum": "$duration"},
                "unique_users": {"$addToSet": "$userId"},
                "first_entry": {"$min": "$entryDate"},
                "last_entry": {"$max": "$entryDate"}
            }}
        ]
        
        res = list(db.timeentries.aggregate(pipeline))
        if not res or res == []:
            return {"status": "no_data", "message": "No records found for this query."}
        total_seconds = res[0].get("total_duration", 0) if res else 0
        unique_contributors = len(res[0].get("unique_users", [])) if res else 0
        first_entry = res[0].get("first_entry") if res else None
        last_entry = res[0].get("last_entry") if res else None
        
        first_entry_str = first_entry.strftime("%Y-%m-%d") if isinstance(first_entry, datetime) else None
        last_entry_str = last_entry.strftime("%Y-%m-%d") if isinstance(last_entry, datetime) else None
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "project": resolved_name,
            "billable": billable,
            "archived": archived,
            "member_count": member_count,
            "total_hours": round(total_seconds / 3600, 2),
            "unique_contributors": unique_contributors,
            "first_entry": first_entry_str,
            "last_entry": last_entry_str,
            "period": period
        }
    except Exception as e:
        return {"error": f"get_project_stats failed: {str(e)}"}


def get_general_count(entity: str) -> dict:
    try:
        count = 0
        if entity == "users":
            count = db.users.count_documents({"archived": {"$ne": True}})
        elif entity == "projects":
            count = db.projects.count_documents({"archived": False, "name": {"$not": re.compile("^_INX-")}})
        elif entity == "tasks":
            count = db.tasks.count_documents({})
        elif entity == "teams":
            count = db.groups.count_documents({})
        else:
            return {"error": f"Unknown entity '{entity}'"}
            
        return {"entity": entity, "count": count}
    except Exception as e:
        return {"error": f"get_general_count failed: {str(e)}"}


def get_user_recent_activity(user_name: str) -> dict:
    try:
        user_id, resolved_name, _, err = resolve_user(user_name)
        if err:
            return {"error": err}

        pipeline = [
            {"$match": {"userId": user_id}},
            {"$sort": {"entryDate": -1}},
            {"$limit": 20},
            {"$lookup": {
                "from": "projects",
                "localField": "projectId",
                "foreignField": "_id",
                "as": "project_info"
            }},
            {"$addFields": {
                "project_name": {"$arrayElemAt": ["$project_info.name", 0]}
            }},
            {"$match": {
                "project_name": {
                    "$not": re.compile("^_INX-"),
                    "$ne": None
                }
            }},
            {"$limit": 1},
            {"$project": {
                "_id": 0,
                "project_name": 1,
                "entryDate": 1,
                "duration": 1
            }}
        ]

        res = list(db.timeentries.aggregate(pipeline))
        if not res:
            # Fall back — return most recent entry even if internal
            fallback = db.timeentries.find_one(
                {"userId": user_id},
                sort=[("entryDate", -1)]
            )
            if not fallback:
                return {"user": resolved_name, "message": "No activity found for this user."}
            proj = db.projects.find_one({"_id": fallback.get("projectId")})
            proj_name = proj.get("name", "Unknown") if proj else "Unknown"
            date_val = fallback.get("entryDate")
            date_str = date_val.strftime("%Y-%m-%d") if isinstance(date_val, datetime) else str(date_val)
            return {
                "user": resolved_name,
                "project": proj_name,
                "date": date_str,
                "hours": round(fallback.get("duration", 0) / 3600, 2)
            }

        activity = res[0]
        date_val = activity.get("entryDate")
        date_str = date_val.strftime("%Y-%m-%d") if isinstance(date_val, datetime) else str(date_val)

        return {
            "user": resolved_name,
            "project": activity.get("project_name", "Unknown"),
            "date": date_str,
            "hours": round(activity.get("duration", 0) / 3600, 2)
        }
    except Exception as e:
        return {"error": f"get_user_recent_activity failed: {str(e)}"}


def get_idle_employees(days=7) -> dict:
    try:
        days = int(days)
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        
        active_users = list(db.users.find({"archived": {"$ne": True}}, {"name": 1}))
        
        active_loggers = db.timeentries.distinct("userId", {"entryDate": {"$gte": cutoff_date}})
        active_logger_ids = {uid for uid in active_loggers if uid}
        
        idle_users = [
            u.get("name", "Unknown User")
            for u in active_users
            if u["_id"] not in active_logger_ids
        ]
        
        return {
            "idle_employees": idle_users,
            "days_checked": days,
            "idle_count": len(idle_users)
        }
    except Exception as e:
        return {"error": f"get_idle_employees failed: {str(e)}"}


def get_user_project_hours(user_name: str, start_date: str = None, end_date: str = None, limit=10) -> dict:
    try:
        limit = int(limit)
        user_id, resolved_name, _, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        match_stage = {"userId": user_id}
        date_filter = build_date_filter(start_date, end_date)
        if date_filter:
            match_stage.update(date_filter)
            
        pipeline = [
            {"$match": match_stage},
            {"$group": {"_id": "$projectId", "total_duration": {"$sum": "$duration"}}},
            {"$lookup": {
                "from": "projects", 
                "localField": "_id", 
                "foreignField": "_id", 
                "as": "project_info"
            }},
            {"$project": {
                "_id": 0,
                "name": {"$arrayElemAt": ["$project_info.name", 0]},
                "total_duration": 1
            }},
            {"$match": {"name": {"$not": re.compile("^_INX-"), "$ne": ""}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": limit}
        ]
        
        res = list(db.timeentries.aggregate(pipeline))
        if not res or res == []:
            return {"status": "no_data", "message": "No records found for this query."}
        breakdown = [
            {"project": item.get("name") or "Unknown Project", "hours": round(item.get("total_duration", 0) / 3600, 2)}
            for item in res
        ]
        
        total_seconds = sum(item.get("total_duration", 0) for item in res)
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "user": resolved_name,
            "project_breakdown": breakdown,
            "total_hours": round(total_seconds / 3600, 2),
            "period": period
        }
    except Exception as e:
        return {"error": f"get_user_project_hours failed: {str(e)}"}


def validate_pipeline(pipeline: list) -> tuple[bool, str]:
    if not isinstance(pipeline, list):
        return False, "Pipeline must be a list"
    
    forbidden = ["$out", "$merge"]
    pipeline_str = str(pipeline)
    for op in forbidden:
        if op in pipeline_str:
            return False, f"Forbidden operator: {op}"
    
    has_limit = any("$limit" in str(stage) for stage in pipeline)
    if not has_limit:
        pipeline.append({"$limit": 100})
    
    return True, ""
