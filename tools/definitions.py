TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_users",
            "description": "Get list of all users in the system with their name, email, role, and active status",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_list",
            "description": "Get list of all projects with name, billable status, and member count",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_hours_by_user",
            "description": "Get total hours logged by each user across all time, sorted by most hours first",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hours_by_project",
            "description": "Get total hours logged per project, sorted by most hours first",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_entries_without_task",
            "description": "Get time entries that have no task assigned, showing which users logged hours without a task",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_timers",
            "description": "Get currently running timers showing which users are actively tracking time right now",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_hours_this_week",
            "description": "Get hours logged by each user during the current week starting from last Monday",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
