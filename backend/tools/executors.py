from database import db
from bson import ObjectId
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_user(name: str):
    user = db.users.find_one({"name": {"$regex": name, "$options": "i"}})
    if not user:
        return None, None, None, f"User '{name}' not found"
    return user["_id"], user["name"], user.get("email"), None


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
    if not start_date and not end_date:
        return {}
    time_cond = {}
    date_cond = {}
    if start_date:
        sd = parse_date(start_date)
        if sd:
            time_cond["$gte"] = sd
            date_cond["$gte"] = sd
    if end_date:
        ed = parse_date(end_date)
        if ed:
            time_cond["$lte"] = ed
            date_cond["$lte"] = ed
    
    # If parsing failed, return empty to prevent breaking query
    if not time_cond and not date_cond:
        return {}
        
    return {"$or": [{"startTime": time_cond}, {"startDate": date_cond}]}

# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------

def get_user_hours(user_name: str, start_date: str = None, end_date: str = None) -> dict:
    try:
        user_id, resolved_name, user_email, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        date_filter = build_date_filter(start_date, end_date)
        
        # Type 1: ObjectId entries
        match_type1 = {"userId": user_id}
        if date_filter:
            match_type1.update(date_filter)
            
        pipeline1 = [
            {"$match": match_type1},
            {"$group": {"_id": None, "total_duration": {"$sum": "$duration"}, "count": {"$sum": 1}}}
        ]
        
        # Type 2: String entries (CSV imports)
        match_conds = [{"user": {"$regex": resolved_name, "$options": "i"}}]
        if user_email:
            match_conds.append({"email": user_email})
            
        match_type2 = {
            "$and": [
                {"$or": match_conds},
                {"$or": [{"userId": {"$exists": False}}, {"userId": None}]}
            ]
        }
        if date_filter:
            match_type2["$and"].append(date_filter)
            
        pipeline2 = [
            {"$match": match_type2},
            {"$group": {"_id": None, "total_duration": {"$sum": "$duration"}, "count": {"$sum": 1}}}
        ]
        
        res1 = list(db.timeentries.aggregate(pipeline1))
        res2 = list(db.timeentries.aggregate(pipeline2))
        
        total_seconds = 0
        entry_count = 0
        
        if res1:
            total_seconds += res1[0].get("total_duration", 0)
            entry_count += res1[0].get("count", 0)
        if res2:
            total_seconds += res2[0].get("total_duration", 0)
            entry_count += res2[0].get("count", 0)
            
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
        user_id, resolved_name, user_email, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        # Step 2: query projects where members array contains that ObjectId
        query = {"members": user_id, "name": {"$not": re.compile("^_INX-")}}
        if not include_archived:
            query["archived"] = {"$ne": True}
            
        cursor = db.projects.find(query, {"name": 1, "billable": 1, "archived": 1, "_id": 0})
        member_projects = list(cursor)
        
        # Step 3: query projects from timeentries string matching user's email or name
        match_conds = [{"user": {"$regex": resolved_name, "$options": "i"}}]
        if user_email:
            match_conds.append({"email": user_email})
            
        time_pipeline = [
            {"$match": {"$or": match_conds, "project": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$project"}}
        ]
        time_projects_res = list(db.timeentries.aggregate(time_pipeline))
        
        project_names = {p["name"] for p in member_projects if "name" in p}
        merged_projects = list(member_projects)
        
        # Step 4: Merge both project lists and deduplicate
        for tp in time_projects_res:
            pname = tp["_id"]
            if pname not in project_names and not pname.startswith("_INX-"):
                p_doc = db.projects.find_one({"name": pname})
                if p_doc:
                    if not include_archived and p_doc.get("archived", False):
                        continue
                    merged_projects.append({
                        "name": p_doc.get("name", pname),
                        "billable": p_doc.get("billable", False),
                        "archived": p_doc.get("archived", False)
                    })
                else:
                    merged_projects.append({
                        "name": pname,
                        "billable": False,
                        "archived": False
                    })
                project_names.add(pname)
                
        return {
            "user": resolved_name,
            "projects": merged_projects,
            "count": len(merged_projects)
        }
    except Exception as e:
        return {"error": f"get_user_projects failed: {str(e)}"}


def get_project_contributors(project_name: str, start_date: str = None, end_date: str = None, limit=10) -> dict:
    try:
        limit = int(limit)
        project_id, resolved_name, err = resolve_project(project_name)
        if err:
            return {"error": err}
            
        date_filter = build_date_filter(start_date, end_date)
        
        # Type 1: ObjectId entries
        match_type1 = {"projectId": project_id}
        if date_filter:
            match_type1.update(date_filter)
            
        pipeline1 = [
            {"$match": match_type1},
            {"$group": {"_id": "$userId", "total_duration": {"$sum": "$duration"}}},
            {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user_info"}},
            {"$project": {
                "_id": 0,
                "name": {"$arrayElemAt": ["$user_info.name", 0]},
                "total_duration": 1
            }}
        ]
        
        # Type 2: String entries
        match_type2 = {
            "$and": [
                {"project": {"$regex": resolved_name, "$options": "i"}},
                {"$or": [{"userId": {"$exists": False}}, {"userId": None}]}
            ]
        }
        if date_filter:
            match_type2["$and"].append(date_filter)
            
        pipeline2 = [
            {"$match": match_type2},
            {"$group": {"_id": "$user", "total_duration": {"$sum": "$duration"}}},
            {"$project": {
                "_id": 0,
                "name": "$_id",
                "total_duration": 1
            }}
        ]
        
        res1 = list(db.timeentries.aggregate(pipeline1))
        res2 = list(db.timeentries.aggregate(pipeline2))
        
        # Merge both result lists
        contributors_map = {}
        for item in res1 + res2:
            name = item.get("name")
            if not name:
                continue
            if name not in contributors_map:
                contributors_map[name] = 0
            contributors_map[name] += item.get("total_duration", 0)
            
        sorted_contributors = sorted([
            {"name": name, "hours": round(dur / 3600, 2)} 
            for name, dur in contributors_map.items()
        ], key=lambda x: x["hours"], reverse=True)
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "project": resolved_name,
            "contributors": sorted_contributors[:limit],
            "period": period
        }
    except Exception as e:
        return {"error": f"get_project_contributors failed: {str(e)}"}


def get_active_employees(start_date: str = None, end_date: str = None, limit=10) -> dict:
    try:
        limit = int(limit)
        date_filter = build_date_filter(start_date, end_date)
        
        # Type 1: ObjectId entries
        match_type1 = {"userId": {"$ne": None}}
        if date_filter:
            match_type1.update(date_filter)
            
        pipeline1 = [
            {"$match": match_type1},
            {"$group": {"_id": "$userId", "total_duration": {"$sum": "$duration"}}},
            {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user_info"}},
            {"$project": {"_id": 0, "name": {"$arrayElemAt": ["$user_info.name", 0]}, "total_duration": 1}}
        ]
        
        # Type 2: String entries
        match_type2 = {
            "$and": [
                {"user": {"$ne": "", "$exists": True}},
                {"$or": [{"userId": {"$exists": False}}, {"userId": None}]}
            ]
        }
        if date_filter:
            match_type2["$and"].append(date_filter)
            
        pipeline2 = [
            {"$match": match_type2},
            {"$group": {"_id": "$user", "total_duration": {"$sum": "$duration"}}},
            {"$project": {"_id": 0, "name": "$_id", "total_duration": 1}}
        ]
        
        res1 = list(db.timeentries.aggregate(pipeline1))
        res2 = list(db.timeentries.aggregate(pipeline2))
        
        employees_map = {}
        for item in res1 + res2:
            name = item.get("name")
            if not name:
                continue
            if name not in employees_map:
                employees_map[name] = 0
            employees_map[name] += item.get("total_duration", 0)
            
        sorted_employees = sorted([
            {"name": name, "hours": round(dur / 3600, 2)} 
            for name, dur in employees_map.items()
        ], key=lambda x: x["hours"], reverse=True)
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "employees": sorted_employees[:limit],
            "period": period
        }
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
        
        date_filter = build_date_filter(start_date, end_date)
        
        # Type 1: ObjectId entries
        match_type1 = {"projectId": project_id}
        if date_filter:
            match_type1.update(date_filter)
            
        pipeline1 = [
            {"$match": match_type1},
            {"$group": {
                "_id": None,
                "total_duration": {"$sum": "$duration"},
                "unique_users": {"$addToSet": "$userId"},
                "first_entry": {"$min": "$startTime"},
                "last_entry": {"$max": "$startTime"}
            }}
        ]
        
        # Type 2: String entries
        match_type2 = {"project": {"$regex": resolved_name, "$options": "i"}}
        if date_filter:
            match_type2 = {"$and": [{"project": {"$regex": resolved_name, "$options": "i"}}, date_filter]}
            
        pipeline2 = [
            {"$match": match_type2},
            {"$group": {
                "_id": None,
                "total_duration": {"$sum": "$duration"},
                "unique_users": {"$addToSet": "$user"},
                "first_entry": {"$min": "$startDate"},
                "last_entry": {"$max": "$startDate"}
            }}
        ]
        
        res1 = list(db.timeentries.aggregate(pipeline1))
        res2 = list(db.timeentries.aggregate(pipeline2))
        
        total_seconds = 0
        unique_contributors_set = set()
        first_entry = None
        last_entry = None
        
        if res1:
            total_seconds += res1[0].get("total_duration", 0)
            unique_contributors_set.update(res1[0].get("unique_users", []))
            f1 = res1[0].get("first_entry")
            l1 = res1[0].get("last_entry")
            if f1 and (not first_entry or f1 < first_entry): first_entry = f1
            if l1 and (not last_entry or l1 > last_entry): last_entry = l1
            
        if res2:
            total_seconds += res2[0].get("total_duration", 0)
            unique_contributors_set.update(res2[0].get("unique_users", []))
            f2 = res2[0].get("first_entry")
            l2 = res2[0].get("last_entry")
            if f2 and (not first_entry or f2 < first_entry): first_entry = f2
            if l2 and (not last_entry or l2 > last_entry): last_entry = l2
            
        total_hours = round(total_seconds / 3600, 2)
        unique_contributors = len(unique_contributors_set)
        
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
            "total_hours": total_hours,
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
            count = db.teams.count_documents({})
        else:
            return {"error": f"Unknown entity '{entity}'"}
            
        return {"entity": entity, "count": count}
    except Exception as e:
        return {"error": f"get_general_count failed: {str(e)}"}


def get_user_recent_activity(user_name: str) -> dict:
    try:
        user_id, resolved_name, user_email, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        # Type 1: ObjectId entries
        pipeline1 = [
            {"$match": {"userId": user_id}},
            {"$sort": {"startTime": -1}},
            {"$lookup": {"from": "projects", "localField": "projectId", "foreignField": "_id", "as": "project_info"}},
            {"$match": {"project_info.name": {"$not": re.compile("^_INX-")}}},
            {"$limit": 1},
            {"$project": {
                "_id": 0,
                "project_name": {"$arrayElemAt": ["$project_info.name", 0]},
                "start_time": "$startTime",
                "duration": "$duration"
            }}
        ]
        
        # Type 2: String entries
        match_conds = [{"user": {"$regex": resolved_name, "$options": "i"}}]
        if user_email:
            match_conds.append({"email": user_email})
            
        pipeline2 = [
            {"$match": {
                "$and": [
                    {"$or": match_conds},
                    {"project": {"$not": re.compile("^_INX-"), "$ne": ""}}
                ]
            }},
            {"$sort": {"startDate": -1}},
            {"$limit": 1},
            {"$project": {
                "_id": 0,
                "project_name": "$project",
                "start_time": "$startDate",
                "duration": "$duration"
            }}
        ]
        
        res1 = list(db.timeentries.aggregate(pipeline1))
        res2 = list(db.timeentries.aggregate(pipeline2))
        
        recent_entry = None
        
        if res1 and res2:
            date1 = res1[0].get("start_time")
            date2 = res2[0].get("start_time")
            if date1 and date2:
                recent_entry = res1[0] if date1 > date2 else res2[0]
            elif date1:
                recent_entry = res1[0]
            else:
                recent_entry = res2[0]
        elif res1:
            recent_entry = res1[0]
        elif res2:
            recent_entry = res2[0]
            
        if not recent_entry:
            return {"user": resolved_name, "message": "No recent activity found."}
            
        date_str = recent_entry.get("start_time").strftime("%Y-%m-%d %H:%M:%S") if isinstance(recent_entry.get("start_time"), datetime) else str(recent_entry.get("start_time"))
        
        return {
            "user": resolved_name,
            "project": recent_entry.get("project_name") or "Unknown Project",
            "date": date_str,
            "hours": round(recent_entry.get("duration", 0) / 3600, 2)
        }
    except Exception as e:
        return {"error": f"get_user_recent_activity failed: {str(e)}"}


def get_idle_employees(days=7) -> dict:
    try:
        days = int(days)
        from datetime import timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get all active users
        active_users_cursor = db.users.find({"archived": {"$ne": True}})
        active_users = list(active_users_cursor)
        
        # Type 1: Users who logged hours recently (ObjectId)
        pipeline1 = [
            {"$match": {"startTime": {"$gte": cutoff_date}, "userId": {"$ne": None}}},
            {"$group": {"_id": "$userId"}}
        ]
        res1 = list(db.timeentries.aggregate(pipeline1))
        active_user_ids = {item["_id"] for item in res1}
        
        # Type 2: Users who logged hours recently (String)
        pipeline2 = [
            {"$match": {"startDate": {"$gte": cutoff_date}, "user": {"$ne": "", "$exists": True}}},
            {"$group": {"_id": "$user"}}
        ]
        res2 = list(db.timeentries.aggregate(pipeline2))
        active_user_names = {item["_id"].lower() for item in res2 if isinstance(item.get("_id"), str)}
        
        # Find idle users
        idle_users = []
        for u in active_users:
            if u["_id"] in active_user_ids:
                continue
            if u.get("name") and u["name"].lower() in active_user_names:
                continue
            idle_users.append(u.get("name", "Unknown User"))
            
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
        user_id, resolved_name, user_email, err = resolve_user(user_name)
        if err:
            return {"error": err}
            
        date_filter = build_date_filter(start_date, end_date)
        
        # Type 1: ObjectId entries
        match_type1 = {"userId": user_id}
        if date_filter:
            match_type1.update(date_filter)
            
        pipeline1 = [
            {"$match": match_type1},
            {"$group": {"_id": "$projectId", "total_duration": {"$sum": "$duration"}}},
            {"$lookup": {"from": "projects", "localField": "_id", "foreignField": "_id", "as": "project_info"}},
            {"$project": {
                "_id": 0,
                "name": {"$arrayElemAt": ["$project_info.name", 0]},
                "total_duration": 1
            }},
            {"$match": {"name": {"$not": re.compile("^_INX-")}}}
        ]
        
        # Type 2: String entries
        match_conds = [{"user": {"$regex": resolved_name, "$options": "i"}}]
        if user_email:
            match_conds.append({"email": user_email})
            
        match_type2 = {
            "$and": [
                {"$or": match_conds},
                {"$or": [{"userId": {"$exists": False}}, {"userId": None}]}
            ]
        }
        if date_filter:
            match_type2["$and"].append(date_filter)
            
        pipeline2 = [
            {"$match": match_type2},
            {"$group": {"_id": "$project", "total_duration": {"$sum": "$duration"}}},
            {"$project": {
                "_id": 0,
                "name": "$_id",
                "total_duration": 1
            }},
            {"$match": {"name": {"$not": re.compile("^_INX-"), "$ne": ""}}}
        ]
        
        res1 = list(db.timeentries.aggregate(pipeline1))
        res2 = list(db.timeentries.aggregate(pipeline2))
        
        project_map = {}
        for item in res1 + res2:
            p_name = item.get("name")
            if not p_name:
                continue
            if p_name not in project_map:
                project_map[p_name] = 0
            project_map[p_name] += item.get("total_duration", 0)
            
        sorted_projects = sorted([
            {"project": name, "hours": round(dur / 3600, 2)} 
            for name, dur in project_map.items()
        ], key=lambda x: x["hours"], reverse=True)
        
        total_seconds = sum(project_map.values())
        total_hours = round(total_seconds / 3600, 2)
        
        period = "all time"
        if start_date or end_date:
            parts = []
            if start_date: parts.append(f"from {start_date}")
            if end_date: parts.append(f"to {end_date}")
            period = " ".join(parts)
            
        return {
            "user": resolved_name,
            "project_breakdown": sorted_projects[:limit],
            "total_hours": total_hours,
            "period": period
        }
    except Exception as e:
        return {"error": f"get_user_project_hours failed: {str(e)}"}


def validate_pipeline(pipeline: list) -> tuple[bool, str]:
    """Returns (is_safe, error_message)"""
    if not isinstance(pipeline, list):
        return False, "Pipeline must be a list"
    
    forbidden = ["$out", "$merge"]
    pipeline_str = str(pipeline)
    for op in forbidden:
        if op in pipeline_str:
            return False, f"Forbidden operator: {op}"
    
    # Check $limit exists somewhere
    has_limit = any("$limit" in str(stage) for stage in pipeline)
    if not has_limit:
        pipeline.append({"$limit": 100})  # auto-add if missing
    
    return True, ""
