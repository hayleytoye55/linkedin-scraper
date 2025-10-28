import os
import json
import datetime
import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup

# --------------------------
# CONFIGURATION
# --------------------------
SHEET_ID = "1ufd1BMBkisd0T5eUsj4DELBHKP3yQz27ARgqP70VTfA"
SHEET_TAB = "Posts"

# Google credentials (from GitHub Secret)
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

# --------------------------
# LOAD COMPANY LIST
# --------------------------
# We’ll assume your first tab (gid=0) has two columns: Company | LinkedIn URL
company_sheet = client.open_by_key(SHEET_ID).get_worksheet(0)
companies = company_sheet.get_all_values()[1:]  # skip header row

# --------------------------
# SCRAPE PUBLIC POSTS
# --------------------------
def get_latest_posts(company_name, linkedin_url, max_posts=3):
    posts = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(linkedin_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # Grab visible text blocks - LinkedIn hides a lot, so we’ll approximate
        text_blocks = [t.get_text(strip=True) for t in soup.find_all("p")]
        text_blocks = [t for t in text_blocks if len(t) > 40]  # filter very short stuff

        for text in text_blocks[:max_posts]:
            posts.append({
                "Date": datetime.date.today().isoformat(),
                "Company": company_name,
                "Post text": text,
                "Post URL": linkedin_url,
                "Category": "General"
            })
    except Exception as e:
        print(f"Error scraping {company_name}: {e}")
    return posts

# --------------------------
# MAIN: COLLECT AND WRITE
# --------------------------
all_posts = []
for name, url in companies:
    company_posts = get_latest_posts(name, url)
    all_posts.extend(company_posts)

if all_posts:
    rows = [[p["Date"], p["Company"], p["Post text"], p["Post URL"], p["Category"]] for p in all_posts]
    sheet.append_rows(rows, value_input_option="RAW")

print(f"Added {len(all_posts)} posts to the sheet.")
