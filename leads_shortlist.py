import requests
import json
from datetime import datetime
import dateutil.parser
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
SHORTLISTED_TABLE = 'Shortlisted Leads'

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}
print("API KEY LOADED:", os.getenv("AIRTABLE_API_KEY"))
print("BASE ID LOADED:", os.getenv("BASE_ID"))
print("Header:", HEADERS)

# === Helper Functions ===
def get_rows(table, filter_formula):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    params = {'filterByFormula': filter_formula}
    resp = requests.get(url, headers=HEADERS, params=params)
    return resp.json().get('records', [])
    print("PATCH/POST URL:", url)
def get_record_by_id(table, record_id):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}/{record_id}"
    r = requests.get(url, headers=HEADERS)
    return r.json()
    print("PATCH/POST URL:", url)
# === Step 3: Compress Applicant Data ===
def compress_applicant(applicant_record_id):
    # 1. Personal details (should only be 1 linked)
    personal_rows = get_rows(PERSONAL_TABLE, f"Applicant = '{applicant_record_id}'")
    personal = personal_rows[0]['fields'] if personal_rows else {}

    # 2. Work Experience (list)
    work_rows = get_rows(WORK_TABLE, f"Applicant = '{applicant_record_id}'")
    experience = [{
        "company": row['fields'].get("Company"),
        "title": row['fields'].get("Title"),
        "start": row['fields'].get("Start"),
        "end": row['fields'].get("End"),
        "technologies": row['fields'].get("Technologies"),
    } for row in work_rows]

    # 3. Salary Preferences (should be 1 linked)
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
    data = {
        "fields": {
            "Compressed JSON": json.dumps(compressed, indent=2)
        }
    }
    resp = requests.patch(url, headers=HEADERS, data=json.dumps(data))
    if resp.ok:
        print(f"Compressed JSON updated for Applicant: {applicant_record_id}")
    else:
        print("Error updating record:", resp.text)
    return compressed
    print("PATCH/POST URL:", url)
# === Step 5: Shortlisting Logic ===
TIER_1 = {'google', 'meta', 'openai', 'microsoft', 'apple', 'amazon'}
SHORTLIST_COUNTRIES = ['us', 'united states', 'canada', 'uk', 'united kingdom', 'germany', 'india']

def get_years_of_experience(experience_list):
    years = 0
    for job in experience_list:
        try:
            start = dateutil.parser.parse(job.get("start")) if job.get("start") else None
            end = dateutil.parser.parse(job.get("end")) if job.get("end") else datetime.now()
            if start:
                duration = (end - start).days / 365.25
                years += max(0, duration)
        except:
            continue
    return years

def is_tier_1_company(experience_list):
    for job in experience_list:
        company = str(job.get('company', '') or '').lower()
        if any(big in company for big in TIER_1):
            return True
    return False

def is_location_qualified(location):
    location = str(location or "").lower()
    return any(country in location for country in SHORTLIST_COUNTRIES)

def check_shortlist_logic(compressed_json):
    experience = compressed_json.get("experience", [])
    years = get_years_of_experience(experience)
    in_top_company = is_tier_1_company(experience)
    exp_ok = years >= 4 or in_top_company

    salary = compressed_json.get("salary", {})
    rate_ok = (salary.get("rate") is not None and salary.get("rate") <= 100)
    avail_ok = (salary.get("availability") is not None and salary.get("availability") >= 20)

    personal = compressed_json.get("personal", {})
    loc_ok = is_location_qualified(personal.get("location"))

    all_ok = exp_ok and rate_ok and avail_ok and loc_ok

    reasons = []
    if not exp_ok:
        reasons.append("Insufficient experience (needs 4+ years or Tier-1 company)")
    if not rate_ok:
        reasons.append("Preferred rate exceeds $100/hr")
    if not avail_ok:
        reasons.append("Availability below 20 hrs/week")
    if not loc_ok:
        reasons.append("Not in a qualifying country")
    if all_ok:
        reasons = ["All criteria met."]
    return all_ok, "; ".join(reasons)

def create_shortlisted_lead(applicant_id, compressed_json, score_reason):
    fields = {
        "Applicant": [applicant_id],
        "Compressed JSON": json.dumps(compressed_json, indent=2),
        "Score Reason": score_reason
        # "Created At" is filled by Airtable automatically
    }
    url = f"https://api.airtable.com/v0/{BASE_ID}/{SHORTLISTED_TABLE.replace(' ', '%20')}"
    resp = requests.post(url, headers=HEADERS, data=json.dumps({"fields": fields}))
    if resp.ok:
        print("Shortlisted lead created!")
    else:
        print("Error creating shortlisted lead:", resp.text)

# === Compress and Shortlist ===
def compress_and_shortlist(applicant_id):
    # Compress data and write JSON
    rec = get_record_by_id(APPLICANTS_TABLE, applicant_id)
    compressed_json_str = rec.get('fields', {}).get('Compressed JSON')
    if not compressed_json_str:
        print("No Compressed JSON. Run compression step first.")
        return
    compressed = json.loads(compressed_json_str)

    # Run shortlist logic
    is_shortlisted, score_reason = check_shortlist_logic(compressed)
    print("Score reason:", score_reason)
    if is_shortlisted:
        create_shortlisted_lead(applicant_id, compressed, score_reason)
    else:
        print("Applicant did not meet shortlist criteria.")

if __name__ == '__main__':
    rid = "recKoEZb0kGGv5Prv"
    compress_applicant(rid)
    compress_and_shortlist(rid)