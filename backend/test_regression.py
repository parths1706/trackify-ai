import requests
import uuid
import time

API_URL = "http://127.0.0.1:8000/api/v1/chat"

questions = [
    "Who logged the most hours this month?",
    "How many billable hours did the Mobile team log last month?",
    "Which employee worked on the most projects this month?",
    "Compare total hours logged by each team this week",
    "Who worked on Beva web app and how many hours did each person log?",
    "Which projects had zero hours logged this week?",
    "Show me Kartik's hours for each day this week",
    "Who hasn't logged any hours today?",
    "What percentage of hours this month were billable vs non-billable?",
    "Which team has been the most productive over the last 3 months?",
    "How do Kartik and Moksha compare in hours logged this month?",
    "Show me this week's hours — now compare it to last week",
    "Which project had the most hours logged by the PHP team last month?",
    "Who logged more than 8 hours on a single day this month?",
    "Give me a summary of last month — total hours, top 3 employees, most active project"
]

print("=== 15 QUESTION REGRESSION TEST ===")
for i, q in enumerate(questions):
    session_id = str(uuid.uuid4())
    req = {
        "messages": [{"role": "user", "content": q}],
        "session_id": session_id
    }
    try:
        resp = requests.post(API_URL, json=req)
        if resp.status_code == 200:
            print(f"Q{i+1} [PASS]: {q}")
        else:
            print(f"Q{i+1} [FAIL HTTP {resp.status_code}]: {q}")
    except Exception as e:
        print(f"Q{i+1} [ERROR]: {q}")
    time.sleep(1) # Prevent rate limits just in case

print("\n=== 2-MESSAGE MEMORY TEST ===")
session_id = str(uuid.uuid4())

q1 = "How many hours did Kartik log this month?"
print(f"User 1: {q1}")
req1 = {
    "messages": [{"role": "user", "content": q1}],
    "session_id": session_id
}
resp1 = requests.post(API_URL, json=req1)
print(f"AI 1: {resp1.json().get('reply', '')}")

q2 = "Which projects did they work on?"
print(f"User 2: {q2}")
req2 = {
    "messages": [{"role": "user", "content": q2}],
    "session_id": session_id
}
resp2 = requests.post(API_URL, json=req2)
reply2 = resp2.json().get('reply', '')
print(f"AI 2: {reply2}")

if "projects" in reply2.lower() and ("blackbox" in reply2.lower() or "not sure" not in reply2.lower()):
    print("\nMEMORY TEST: PASS")
else:
    print("\nMEMORY TEST: FAIL")
