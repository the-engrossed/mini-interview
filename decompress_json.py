import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION ===
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
BASE_ID = os.getenv('BASE_ID')
APPLICANTS_TABLE = 'Applicants'
PERSONAL_TABLE = 'Personal Details'
WORK_TABLE = 'Work Experience'
SALARY_TABLE = 'Salary Preferences'

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

def get_record_by_id(table, record_id):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}/{record_id}"
    r = requests.get(url, headers=HEADERS)
    return r.json()

def get_linked_records(table, applicant_id):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    params = {'filterByFormula': f"Applicant = '{applicant_id}'"}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json().get('records', [])

def upsert_personal_details(applicant_id, personal_json):
    # Remove old records
    records = get_linked_records(PERSONAL_TABLE, applicant_id)
    for rec in records:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{PERSONAL_TABLE}/{rec['id']}", headers=HEADERS)
    # Add new
    fields = {
        "Full Name": personal_json.get("name"),
        "Location": personal_json.get("location"),
        "Email": personal_json.get("email"),
        "LinkedIn": personal_json.get("linkedin"),
        "Applicant": [applicant_id]
    }
    requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PERSONAL_TABLE}", headers=HEADERS, data=json.dumps({"fields": fields}))

def upsert_salary_preferences(applicant_id, salary_json):
    # Remove old records
    records = get_linked_records(SALARY_TABLE, applicant_id)
    for rec in records:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{SALARY_TABLE}/{rec['id']}", headers=HEADERS)
    # Add new
    fields = {
        "Preferred Rate": salary_json.get("rate"),
        "Minimum Rate": salary_json.get("minimum_rate"),
        "Currency": salary_json.get("currency"),
        "Availability": salary_json.get("availability"),
        "Applicant": [applicant_id]
    }
    requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{SALARY_TABLE}", headers=HEADERS, data=json.dumps({"fields": fields}))

def upsert_work_experience(applicant_id, experience_json):
    # Remove previous experience
    records = get_linked_records(WORK_TABLE, applicant_id)
    for rec in records:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{WORK_TABLE}/{rec['id']}", headers=HEADERS)
    # Add each new experience
    for job in experience_json or []:
        fields = {
            "Company": job.get("company"),
            "Title": job.get("title"),
            "Start": job.get("start"),
            "End": job.get("end"),
            "Technologies": job.get("technologies"),
            "Applicant": [applicant_id]
        }
        requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{WORK_TABLE}", headers=HEADERS, data=json.dumps({"fields": fields}))

def decompress_json_to_child_tables(applicant_id):
    # Step 1: Fetch Compressed JSON from Applicants table
    rec = get_record_by_id(APPLICANTS_TABLE, applicant_id)
    comp_json_str = rec.get('fields', {}).get('Compressed JSON')
    if not comp_json_str:
        print("No Compressed JSON found!")
        return
    comp_json = json.loads(comp_json_str)

    # Step 2: Upsert child tables from JSON
    upsert_personal_details(applicant_id, comp_json.get("personal", {}))
    upsert_work_experience(applicant_id, comp_json.get("experience", []))
    upsert_salary_preferences(applicant_id, comp_json.get("salary", {}))
    print("Child tables updated from compressed JSON.")

if __name__ == '__main__':
    print("Starting decompression test")
    decompress_json_to_child_tables("recKoEZbOkGgV5prv") 
