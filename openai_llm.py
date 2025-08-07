import requests
import json
import openai
import os
from dotenv import load_dotenv

load_dotenv()


# ---- CONFIGURE OPENAI -----
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# ---- Your Airtable setup goes here ----
AIRTABLE_API_KEY = 'patLT7zSw8QEiyUoq.36531874fc35732f40a89ff83bb5cadec26ba2bbe85e44686f04c5d2be2ffb22'
BASE_ID = 'apptYweCILGTeVvB6'
APPLICANTS_TABLE = 'Applicants'
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

def get_record_by_id(table, record_id):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}/{record_id}"
    r = requests.get(url, headers=HEADERS)
    return r.json()

def enrich_with_llm(applicant_id):
    # 1. Get Compressed JSON from Airtable
    rec = get_record_by_id(APPLICANTS_TABLE, applicant_id)
    compressed_json_str = rec.get('fields', {}).get('Compressed JSON')
    if not compressed_json_str:
        print("No Compressed JSON in this applicant record.")
        return False

    # 2. Compose LLM prompt
    prompt = f"""
    You are a recruiting analyst. Given this JSON applicant profile, do four things:
    {compressed_json_str}
    1. Provide a concise 75-word summary.
    2. Rate overall candidate quality from 1-10 (higher is better).
    3. List any data gaps or inconsistencies you notice.
    4. Suggest up to three follow-up questions to clarify gaps.

    Return exactly:
    Summary: <text>
    Score: <integer>
    Issues: <comma-separated list or 'None'>
    Follow-Ups: <bullet list>
    """
    # 3. Query LLM
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    reply = response['choices'][0]['message']['content']

    # 4. Extract JSON from LLM reply
    try:
        llm_result = json.loads(reply)
    except Exception:
        print("LLM did not return valid JSON! Raw reply:")
        print(reply)
        return False

    # 5. Write data back to Airtable
    update_fields = {
        "LLM Summary": llm_result.get("summary"),
        "LLM Score": llm_result.get("score"),
        "LLM Follow-Ups": "\n".join(llm_result.get("follow_up_questions", []))
    }
    url = f"https://api.airtable.com/v0/{BASE_ID}/{APPLICANTS_TABLE}/{applicant_id}"
    resp = requests.patch(url, headers=HEADERS, data=json.dumps({"fields": update_fields}))
    if resp.ok:
        print("LLM enrichment written for Applicant:", applicant_id)
        return True
    else:
        print("Error updating record:", resp.text)
        return False
