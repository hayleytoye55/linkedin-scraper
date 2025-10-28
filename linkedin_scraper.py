import os
import json
import datetime
from datetime import timedelta
import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup

# --------------------------
# CONFIGURATION
# --------------------------
SHEET_ID = "1ufd1BMBkisd0T5eUsj4DELBHKP3yQz27ARgqP70VTfA"
SHEET_TAB = "Posts"

# Google credentials from GitHub Secret
creds_json = os.environ.get("GOOGLE_CREDS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

# Load company list from first tab (Company | LinkedIn URL)
company_sheet = client.open_by_key(SHEET_ID).get_worksheet(0)
companies = company_sheet.get_all_values()[1:]  # skip header

# --------------------------
# KEYWORD CATEGORIES
# --------------------------
keywords = {
    "Funding": ["funding", "raised", "investment", "seed", "series a", "series b"],
    "Launch/Product": ["launch", "released", "introduced", "new product", "beta", "live", "announce", "announcement"],
    "Partnership": ["partnered", "collaborated", "alliance", "joined forces"]
}

# --------------------------
# SCRAPE PUBLIC POSTS
# --------------------------
def get_latest_posts(company_name, linkedin_url, max_posts=5):
    posts = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(linkedin_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # Find posts (simplified; grabs visible paragraphs and their links)
        text_blocks = soup.find_all("p")
        for p in text_blocks[:max_posts]:
            post_text = p.get_text(strip=True)
            if len(post_text) < 40:  # ignore very short
                continue

            # Try to get a post URL if available
            post_link_tag = p.find_parent("a", href=True)
            if post_link_tag and "feed/update" in post_link_tag["href"]:
                post_url = "https://www.linkedin.com" + post_link_tag["href"].split("?")[0]
            else:
                post_url = linkedin_url  # fallback

            # Try to get a post date from <time datetime="...">
            time_tag = p.find_parent("div").find("time")
            if time_tag and time_tag.has_attr("datetime"):
                post_date = time_tag["datetime"].split("T")[0]
            else:
                post_date = datetime.date.today().isoformat()  # fallback

            # Filter posts in last 7 days only
            post_datetime = datetime.datetime.strptime(post_date, "%Y-%m-%d").date()
            if post_datetime < (datetime.date.today() - timedelta(days=7)):
                continue

            # Determine category
            category = "General"
            for key, words in keywords.items():
                if any(word.lower() in post_text.lower() for word in words):
                    category = key
                    break

            posts.append({
                "Date": post_date,
                "Company": company_name,
                "Post text": post_text,
                "Post URL": post_url,
                "Category": category
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
