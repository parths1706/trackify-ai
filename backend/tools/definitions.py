TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_hours",
            "description": "Get total hours a specific person logged in a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "Full or partial name of the employee to look up"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start of the date range in YYYY-MM-DD format (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of the date range in YYYY-MM-DD format (optional)"
                    }
                },
                "required": ["user_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_projects",
            "description": "Get all projects a specific person is assigned to (is a member of).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "Full or partial name of the employee"
                    },
                    "include_archived": {
                        "type": "boolean",
                        "description": "Whether to include archived projects (default: false)"
                    }
                },
                "required": ["user_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_contributors",
            "description": "Get a ranked list of who worked on a project and how many hours each person logged.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Full or partial name of the project"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start of the date range in YYYY-MM-DD format (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of the date range in YYYY-MM-DD format (optional)"
                    },
                    "limit": {
                        "type": "string",
                        "description": "Maximum number of contributors to return (e.g., '10')"
                    }
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_employees",
            "description": "Get employees ranked by total hours worked in a given period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start of the date range in YYYY-MM-DD format (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of the date range in YYYY-MM-DD format (optional)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_stats",
            "description": "Get summary statistics for a specific project including total hours, number of contributors, and activity date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Full or partial name of the project"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start of the date range in YYYY-MM-DD format (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of the date range in YYYY-MM-DD format (optional)"
                    }
                },
                "required": ["project_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_general_count",
            "description": "Count the total number of users, projects, tasks, or teams in the system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "enum": ["users", "projects", "tasks", "teams"],
                        "description": "The type of entity to count"
                    }
                },
                "required": ["entity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_recent_activity",
            "description": "Get the most recent time entry for a user — what project they last worked on and when.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {
                        "type": "string",
                        "description": "Full or partial name of the employee"
                    }
                },
                "required": ["user_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_idle_employees",
            "description": "Find employees who have not logged any hours in the last N days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "string",
                        "description": "Number of days to look back for activity (e.g., '7')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_project_hours",
            "description": "Get a breakdown of hours a specific person logged per project, optionally filtered by date range. Use this when asked which projects someone worked on in a period, or how many hours they spent on each project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "The name of the employee"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                    "limit": {"type": "string", "description": "Max number of projects to return, default 10"}
                },
                "required": ["user_name"]
            }
        }
    }
]
