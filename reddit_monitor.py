# This script loads the OpenAI API key from the OPENAI_API_KEY environment variable.
# For local development, you can create a .env file with OPENAI_API_KEY=sk-... and it will be loaded automatically.

import praw
import openai
import os
from datetime import datetime
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional for production/cloud

# Reddit API credentials
CLIENT_ID = 'fMdeeGPD8Pri-NALYFuKJg'
CLIENT_SECRET = 'kiICiNbKDs231Ozk_woPju-UIvD38g'
USER_AGENT = 'script:Premium:1.0 (by /u/yao-ming-221566)'

# Business keyword to search for
KEYWORDS = (
    'Wix AND (billing OR subscription OR domain OR payment OR refund) AND '
    '(problem OR issue OR can\'t OR unable OR error OR broken OR stuck OR not working OR declined OR charged twice OR no refund OR complaint)'
)

# OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set. Please set it in your environment, deployment platform, or a .env file.")
openai.api_key = openai_api_key

# Output file
OUTPUT_FILE = 'result.txt'

# Prompt template (without actual post text)
PROMPT_TEMPLATE = (
    "Is this Reddit post a user complaint about Wix? "
    "If yes, what is the complaint about? Summarize the complaint in 1-2 sentences. "
    "If not, reply 'Not a complaint.'\n\n"
    "Post:\n[POST_TEXT]"
)

def search_reddit(keywords, limit=50):
    results = []
    seen_titles = set()
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    for submission in reddit.subreddit('wix+wixhelp').search(keywords, limit=100):
        title_lower = submission.title.lower()
        if title_lower not in seen_titles:
            created_utc = submission.created_utc
            created_date = datetime.utcfromtimestamp(created_utc).strftime('%Y-%m-%d %H:%M:%S')
            results.append({
                'link': f'https://www.reddit.com{submission.permalink}',
                'title': submission.title,
                'text': submission.selftext,
                'subreddit': submission.subreddit.display_name.lower(),
                'created_date': created_date,
                'created_utc': created_utc
            })
            seen_titles.add(title_lower)
    # Sort by creation date descending
    results.sort(key=lambda x: x['created_utc'], reverse=True)
    return results[:limit]

def is_complaint(text):
    prompt = (
        "Is this Reddit post a user complaint about Wix? "
        "If yes, what is the complaint about? Summarize the complaint in 1-2 sentences. "
        "If not, reply 'Not a complaint.'\n\n"
        f"Post:\n{text}"
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI error: {e}"

def classify_complaint(text):
    prompt = (
        "Classify this Reddit post about Wix into one of the following categories: "
        "Billing (related to refunds, prices), Subscriptions (renewals, cancellation), or Domains. "
        "Reply with only the category name.\n\nPost:\n" + text
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"

def write_complaints_to_file(complaints, all_mentions=None):
    run_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    output_lines = []
    output_lines.append(f"=== Run at {run_time} ===\n")
    output_lines.append(f"Reddit Query: {KEYWORDS}\n")
    if all_mentions is not None:
        output_lines.append(f"Number of posts returned by Reddit API: {len(all_mentions)}\n")
        output_lines.append(f"Titles of posts returned by Reddit API:\n")
        for mention in all_mentions:
            output_lines.append(f"- {mention['title']}\n")
    output_lines.append(f"Number of complaints found: {len(complaints)}\n")
    output_lines.append(f"\nOpenAI Prompt Template (without post text):\n{PROMPT_TEMPLATE}\n")
    output_lines.append(f"\nComplaints (with category and summary):\n")
    for complaint in complaints:
        output_lines.append(
            f"- Link: {complaint['link']}\n  Title: {complaint['title']}\n  Date: {complaint['date']}\n  Category: {complaint['category']}\n  Complaint Summary: {complaint['summary']}\n"
        )
    output_lines.append(f"\nComplaints found: {len(complaints)}\n")
    output_lines.append(f"=== End of Run ===\n\n")

    # Prepend to file so latest run is on top
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            old_content = f.read()
    else:
        old_content = ''
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
        f.write(old_content)

def get_categorized_complaints(limit=20):
    mentions = search_reddit(KEYWORDS, limit=limit)
    complaints = []
    for mention in mentions:
        summary = is_complaint(mention['title'] + '\n' + mention['text'])
        if summary.strip().lower() != 'not a complaint.':
            category = classify_complaint(mention['title'] + '\n' + mention['text'])
            complaints.append({
                "link": mention['link'],
                "title": mention['title'],
                "date": mention['created_date'],
                "category": category,
                "summary": summary
            })
    write_complaints_to_file(complaints, all_mentions=mentions)
    return complaints

if __name__ == "__main__":
    run_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    complaints = get_categorized_complaints(limit=50)
    output_lines = []
    output_lines.append(f"=== Run at {run_time} ===\n")
    output_lines.append(f"Reddit Query: {KEYWORDS}\n")
    output_lines.append(f"Number of complaints found: {len(complaints)}\n")
    output_lines.append(f"\nOpenAI Prompt Template (without post text):\n{PROMPT_TEMPLATE}\n")
    output_lines.append(f"\nComplaints (with category and summary):\n")
    for complaint in complaints:
        output_lines.append(
            f"- Link: {complaint['link']}\n  Title: {complaint['title']}\n  Date: {complaint['date']}\n  Category: {complaint['category']}\n  Complaint Summary: {complaint['summary']}\n"
        )
    output_lines.append(f"\nComplaints found: {len(complaints)}\n")
    output_lines.append(f"=== End of Run ===\n\n")

    # Prepend to file so latest run is on top
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            old_content = f.read()
    else:
        old_content = ''
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
        f.write(old_content) 