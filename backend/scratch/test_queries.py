import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.query_service import (
    get_all_users,
    get_project_list,
    get_total_hours_by_user,
    get_user_hours_this_week
)

print("=== get_all_users ===")
print(get_all_users())

print("\n=== get_project_list ===")
print(get_project_list())

print("\n=== get_total_hours_by_user ===")
print(get_total_hours_by_user())

print("\n=== get_user_hours_this_week ===")
print(get_user_hours_this_week())
