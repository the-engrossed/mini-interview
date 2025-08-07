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
    "Authorization": f"Bearer {AIRTABLE_API_KEY}"
}

# print("Script started")
# print("BASE ID:", BASE_ID)

def get_rows(table, filter_formula):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    params = {'filterByFormula': filter_formula}
    resp = requests.get(url, headers=HEADERS, params=params)
    return resp.json().get('records', [])
# print("Script started")

def compress_applicant(applicant_record_id):
    # 1. Personal details
    personal_rows = get_rows(PERSONAL_TABLE, f"Applicant = '{applicant_record_id}'")
    personal = personal_rows[0]['fields'] if personal_rows else {}

    # 2. Work Experience
    work_rows = get_rows(WORK_TABLE, f"Applicant = '{applicant_record_id}'")
    experience = [{
        "company": row['fields'].get("Company"),
        "title": row['fields'].get("Title"),
        "start": row['fields'].get("Start"),
        "end": row['fields'].get("End"),
        "technologies": row['fields'].get("Technologies"),
    } for row in work_rows]

    # 3. Salary Preferences
    salary_rows = get_rows(SALARY_TABLE, f"Applicant = '{applicant_record_id}'")
    salary = salary_rows[0]['fields'] if salary_rows else {}

    # 4. Compose the compressed JSON
    compressed = {
        "personal": {
            "name": personal.get("Full Name"),
            "email": personal.get("Email"),
            "location": personal.get("Location"),
            "linkedin": personal.get("LinkedIn"),
        },
        "experience": experience,
        "salary": {
            "rate": salary.get("Preferred Rate"),
            "minimum_rate": salary.get("Minimum Rate"),
            "currency": salary.get("Currency"),
            "availability": salary.get("Availability"),
        }
    }

    # 5. Push to the Applicants table
    url = f"https://api.airtable.com/v0/{BASE_ID}/{APPLICANTS_TABLE}/{applicant_record_id}"
    up_headers = dict(HEADERS)
    up_headers["Content-Type"] = "application/json"
    data = {
        "fields": {
            "Compressed JSON": json.dumps(compressed, indent=2)
        }
    }
    resp = requests.patch(url, headers=up_headers, data=json.dumps(data))
    if resp.ok:
        print("Compressed JSON updated for Applicant:", applicant_record_id)
        print("BASE ID:", BASE_ID)
        print("Applicants Table:", APPLICANTS_TABLE)
        print("Record ID to update:", applicant_record_id)
        print("Patch URL:", url)
        print("Headers:", up_headers)
        print("Payload:", json.dumps(data, indent=2))

    else:
        print("Error updating record:", resp.text)

# print("Script started")

if __name__ == '__main__':
    # print("main block entered")
    compress_applicant("recKoEZbOkGgV5prv")
