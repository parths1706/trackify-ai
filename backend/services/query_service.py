from database import db
import datetime

def get_all_users():
    """Returns list of {name, email, role, isActive} from users collection"""
    users = list(db.users.find({}, {"name": 1, "email": 1, "role": 1, "isActive": 1, "_id": 0}))
    return users

def get_total_hours_by_user():
    """Joins timeentries with users on userId and returns total hours per user"""
    pipeline = [
        {
            "$addFields": {
                "user_id_obj": {"$toObjectId": "$userId"}
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id_obj",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        {"$unwind": "$user_info"},
        {
            "$group": {
                "_id": "$user_info.name",
                "totalSeconds": {"$sum": "$duration"}
            }
        },
        {
            "$project": {
                "userName": "$_id",
                "totalHours": {"$divide": ["$totalSeconds", 3600]},
                "_id": 0
            }
        },
        {"$sort": {"totalHours": -1}}
    ]
    return list(db.timeentries.aggregate(pipeline))

def get_hours_by_project():
    """Joins timeentries with projects on projectId and returns total hours per project"""
    pipeline = [
        {
            "$addFields": {
                "project_id_obj": {"$toObjectId": "$projectId"}
            }
        },
        {
            "$lookup": {
                "from": "projects",
                "localField": "project_id_obj",
                "foreignField": "_id",
                "as": "project_info"
            }
        },
        {"$unwind": "$project_info"},
        {
            "$group": {
                "_id": "$project_info.name",
                "totalSeconds": {"$sum": "$duration"}
            }
        },
        {
            "$project": {
                "projectName": "$_id",
                "totalHours": {"$divide": ["$totalSeconds", 3600]},
                "_id": 0
            }
        },
        {"$sort": {"totalHours": -1}}
    ]
    return list(db.timeentries.aggregate(pipeline))

def get_entries_without_task():
    """Returns timeentries where taskId is null with user names"""
    pipeline = [
        {"$match": {"taskId": None}},
        {
            "$addFields": {
                "user_id_obj": {"$toObjectId": "$userId"}
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id_obj",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        {"$unwind": "$user_info"},
        {
            "$project": {
                "userName": "$user_info.name",
                "description": 1,
                "durationHours": {"$divide": ["$duration", 3600]},
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$startTime"}},
                "_id": 0
            }
        }
    ]
    return list(db.timeentries.aggregate(pipeline))

def get_active_timers():
    """Returns timeentries where isRunning is true with user names"""
    pipeline = [
        {"$match": {"isRunning": True}},
        {
            "$addFields": {
                "user_id_obj": {"$toObjectId": "$userId"}
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id_obj",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        {"$unwind": "$user_info"},
        {
            "$project": {
                "userName": "$user_info.name",
                "description": 1,
                "startTime": {"$dateToString": {"format": "%Y-%m-%d %H:%M:%S", "date": "$startTime"}},
                "_id": 0
            }
        }
    ]
    return list(db.timeentries.aggregate(pipeline))

def get_project_list():
    """Returns all projects with member counts"""
    pipeline = [
        {
            "$project": {
                "name": 1,
                "billable": 1,
                "memberCount": {"$size": {"$ifNull": ["$members", []]}},
                "_id": 0
            }
        }
    ]
    return list(db.projects.aggregate(pipeline))

def get_user_hours_this_week():
    """Returns user hours logged since last Monday 00:00 UTC"""
    today = datetime.datetime.utcnow()
    # Find last Monday
    monday = today - datetime.timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    pipeline = [
        {"$match": {"startTime": {"$gte": monday}}},
        {
            "$addFields": {
                "user_id_obj": {"$toObjectId": "$userId"}
            }
        },
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id_obj",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        {"$unwind": "$user_info"},
        {
            "$group": {
                "_id": "$user_info.name",
                "totalSeconds": {"$sum": "$duration"}
            }
        },
        {
            "$project": {
                "userName": "$_id",
                "hoursThisWeek": {"$divide": ["$totalSeconds", 3600]},
                "_id": 0
            }
        }
    ]
    return list(db.timeentries.aggregate(pipeline))

def get_hours_today():
    from datetime import datetime, timezone
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"startTime": {"$gte": today_start}}},
        {"$group": {"_id": "$userId", "totalSeconds": {"$sum": "$duration"}}},
        {
            "$addFields": {
                "user_id_obj": {"$toObjectId": "$_id"}
            }
        },
        {"$lookup": {"from": "users", "localField": "user_id_obj", "foreignField": "_id", "as": "user"}},
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {"$project": {"userName": "$user.name", "hoursToday": {"$round": [{"$divide": ["$totalSeconds", 3600]}, 2]}}}
    ]
    return list(db.timeentries.aggregate(pipeline))

def search_user_by_name(name: str):
    import re
    regex = re.compile(name, re.IGNORECASE)
    users = list(db.users.find(
        {"name": {"$regex": regex}},
        {"name": 1, "email": 1, "role": 1, "isActive": 1, "_id": 0}
    ))
    return users
