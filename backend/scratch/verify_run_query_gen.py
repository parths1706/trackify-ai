import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.graph_service import run_graph

print("Running graph on complex query...")
ans = run_graph("Compare hours logged by all members of the Design team this month")
print("\nFinal Answer:")
print(ans)
