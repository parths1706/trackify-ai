import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL
import json

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

schema_prompt = """You are a MongoDB aggregation pipeline expert for a time tracking system.
Generate ONLY a valid JSON aggregation pipeline array. No explanation. No markdown.
Just the raw JSON array starting with [ and ending with ].

DATABASE SCHEMA:

Collection: timeentries (TWO types — handle BOTH in every query)
  Type 1 (live): userId: ObjectId, projectId: ObjectId, startTime: Date, endTime: Date, duration: Number (seconds)
  Type 2 (imported): user: String (name), email: String, project: String, startDate: Date, endDate: Date, duration: Number (seconds)

Collection: users — _id: ObjectId, name: String, email: String, role: String
Collection: projects — _id: ObjectId, name: String, members: [ObjectId], status: String
Collection: groups — _id: ObjectId, name: String, memberIds: [ObjectId]
Collection: teams — _id: ObjectId, name: String, members: [ObjectId]

RULES (never break these):
- Date filter: always use $or covering both startTime and startDate
- User filter: check both userId (via $lookup on users) and user string field
- Project filter: check both projectId (via $lookup on projects) and project string field  
- Always exclude projects starting with "_INX-"
- Always include { $limit: 100 }
- duration is SECONDS — divide by 3600 for hours, round to 2 decimal places
- Never use $out or $merge
- Return human-readable field names

CONVERSATION CONTEXT:
No previous conversation.

QUESTION: Compare hours logged by all members of the Design team this month

Return ONLY the pipeline JSON array:"""

print("Running Gemini call...")
response = model.generate_content(schema_prompt)
text = response.text.strip()
print("\n=== RAW TEXT ===")
print(text)

start_idx = text.find('[')
end_idx = text.rfind(']')
if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
    extracted = text[start_idx:end_idx + 1]
    try:
        parsed = json.loads(extracted)
        print("\n=== PARSED SUCCESSFULLY ===")
    except Exception as e:
        print("\n=== PARSE FAILED ===")
        print(e)
        # Find the line around the error
        lines = extracted.split('\n')
        print("Lines around error:")
        for idx, line in enumerate(lines):
            print(f"{idx+1}: {line}")
else:
    print("\nCould not find outer brackets '[' and ']'")
