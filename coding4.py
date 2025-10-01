import openai 
from openai import OpenAI
import os
import pandas as pd
import requests
import bs4
import json
import re
from datetime import datetime
from supabase import create_client, Client


SUPABASE_URL = "https://djosyykbmsyikyhcodhg.supabase.co"
SUPABASE_KEY = ""
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

endpoint = "https://cdong1--azure-proxy-web-app.modal.run"
api_key = ""
deployment_name = "gpt-4o"
client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

scrape_url = "https://myanimelist.net/topanime.php"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(scrape_url, headers=headers)
soup = bs4.BeautifulSoup(response.text, 'html.parser')


anime_data = []

for entry in soup.select(".ranking-list")[:10]:
    title = entry.select_one(".detail h3 a").get_text(strip=True)
    link = entry.select_one(".detail h3 a")["href"]

    # Score box
    score_tag = entry.select_one(".score-label")
    score = score_tag.get_text(strip=True) if score_tag else None

    # Info text (type, episodes, dates)
    info_tag = entry.select_one(".information")
    info_text = info_tag.get_text(" ", strip=True) if info_tag else ""
    
    # Extract episode count
    ep_count = None
    ep_match = re.search(r"(\d+)\s*eps", info_text)
    if ep_match:
        ep_count = int(ep_match.group(1))
        
    # Extract start and ending year
    start_year, end_year = None, None
    if " - " in info_text:
        date_part = info_text.split(") ")[-1]  
        start_month_year, end_month_year = date_part.split(" - ")
        start_year = start_month_year.strip()[-4:]  
        end_year = end_month_year.strip()[-4:]
    elif info_text:
        date_part = info_text.split(") ")[-1]
        start_year = date_part.strip()[-4:]
        end_year = start_year

    anime_data.append({
        "title": title,
        "score": score,
        "episodes": ep_count,
        "start_year": start_year,
        "end_year": end_year,
    })

for a in anime_data:
    print(a)


# Debug preview
import json
print(json.dumps(anime_data[:3], indent=2))
text_blob = "\n".join([f"{d['title']} {d['score']} {d['episodes']} {d['start_year']} {d['end_year']}" for d in anime_data])


output_dir = "data"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "animeData_blob.txt")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(text_blob)

print(f"Saved blob to: {output_file}")
print(text_blob[:305])  

schema_instruction = """
You are a data extractor. Only return valid JSON.

Extract the first 10 anime and return valid JSON ONLY.:

schema:
    [
        {
    "title": "Attack on Titan",
    "score": "9.29"
    "episodes": 87,
    "start_year": "2013",
    "end_year": "2025",
        },
    ]


Rules:
- Always output strict JSON starting with `[` and ending with `]`.
- Use schema as base, but adapt to the data you see for first 5 anime.
- If end year not available, use 2025 as ending year.
- Do not include numbering (1., 2., 3.) in the titles.
- If data is missing, put "placeholder".

"""


response = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {"role": "developer", "content": schema_instruction},
        {"role": "user", "content": text_blob},
    ],
)

json_blob = response.choices[0].message.content.strip()

print("Raw LLM output:\n", json_blob)

# Parse and save structured data
try:
    parsed = json.loads(json_blob)
except json.JSONDecodeError as e:
    print("LLM did not return valid JSON:", e)
    raise

with open("data/structured_anime.json", "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2)

anime_df = pd.DataFrame(parsed)
print(anime_df.head())

# Upsert into Supabase
rows = []
for item in parsed:
    rows.append({
        "title": item.get("title"),
        "score": item.get("score"),
        "episode_count": item.get("episodes"),
        "start_year": item.get("start_year"),
        "end_year": item.get("end_year") if item.get("end_year") else "2025",
        "updated_at": datetime.utcnow().isoformat()
    })


response = supabase.table("top_anime").upsert(rows).execute()

