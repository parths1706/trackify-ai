import requests

def test_persistence():
    url = "http://127.0.0.0:8000/chat"
    session_id = "test_persistence_thread_1"
    
    print("--- Request 1 ---")
    req1 = {
        "messages": [{"role": "user", "content": "How many hours did Kartik log this month?"}],
        "session_id": session_id
    }
    resp1 = requests.post("http://127.0.0.1:8000/api/v1/chat", json=req1)
    print(resp1.json())
    
    print("\n--- Request 2 ---")
    # Normally frontend sends full history. Here we just send the follow-up.
    # Note: the API expects the last message to be the user message.
    # We won't include the first request/response in the messages list.
    req2 = {
        "messages": [{"role": "user", "content": "Which projects did they work on?"}],
        "session_id": session_id
    }
    resp2 = requests.post("http://127.0.0.1:8000/api/v1/chat", json=req2)
    print(resp2.json())

if __name__ == "__main__":
    test_persistence()
