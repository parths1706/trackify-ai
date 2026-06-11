import sys
sys.path.insert(0, '.')
import os
from dotenv import load_dotenv
load_dotenv()

from services.graph_service import compiled_graph, run_graph

print("=== VERIFYING GRAPH COMPILE ===")
try:
    print("Graph compiled successfully.")
except Exception as e:
    print("Graph compilation failed:", e)
    sys.exit(1)

print("\n=== RUNNING GREETING TEST (PATH: direct) ===")
try:
    response = run_graph("Hey, what can you help me with?")
    print("Response:", response)
except Exception as e:
    print("Greeting test failed:", e)
