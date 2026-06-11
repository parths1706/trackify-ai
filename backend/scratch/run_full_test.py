import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.graph_service import run_graph

def run_test(question: str, history: list = []):
    print(f"\n==============================")
    print(f"USER: {question}")
    if history:
        print("CONVERSATION HISTORY:")
        for m in history:
            print(f"  {m['role']}: {m['content']}")
    response = run_graph(question, history)
    print(f"ASSISTANT: {response}")
    return {"role": "assistant", "content": response}

# Test 1: Simple known executor query
msg1 = {"role": "user", "content": "How many hours did Raj log this week?"}
res1 = run_test(msg1["content"])

# Test 2: Memory test (two parts)
msg2_part1 = {"role": "user", "content": "What project is Sonu working on?"}
res2_part1 = run_test(msg2_part1["content"])

history_2 = [msg2_part1, res2_part1]
msg2_part2 = {"role": "user", "content": "How many hours did he spend on that?"}
res2_part2 = run_test(msg2_part2["content"], history_2)

# Test 3: Multi test
msg3 = {"role": "user", "content": "Who are the most active employees and which projects are they on?"}
res3 = run_test(msg3["content"])

# Test 4: Complex test (MongoDB query generation via Gemini)
msg4 = {"role": "user", "content": "Compare hours logged by all members of the Design team this month"}
res4 = run_test(msg4["content"])

# Test 5: Greeting / Direct answer
msg5 = {"role": "user", "content": "Hey, what can you help me with?"}
res5 = run_test(msg5["content"])
