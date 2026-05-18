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
                        "type": "integer",
                        "description": "Maximum number of contributors to return (default: 10)"
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
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of employees to return (default: 10)"
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
    }
]
