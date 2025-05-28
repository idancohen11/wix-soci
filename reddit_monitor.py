# This script loads the OpenAI API key from the OPENAI_API_KEY environment variable.
# For local development, you can create a .env file with OPENAI_API_KEY=sk-... and it will be loaded automatically.

import praw
import openai
import os
from datetime import datetime
import json
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
        "You are a classification assistant. Your job is to identify complaints about Wix's billing, subscriptions, domains, and Google Workspace services.\n"
        "\n🚨 CRITICAL RULE: ONLY classify as complaint IF the post is about:\n"
        "1. USER paying money TO WIX and having billing/subscription issues, OR\n"
        "2. Domain connectivity/management/purchase issues through Wix, OR  \n"
        "3. Google Workspace integration/purchase issues through Wix\n"
        "4. AND it's a complaint/problem (not just a question about how to do something)\n"
        "\n✅ ONLY INCLUDE these specific complaint types:\n"
        "- User being charged by Wix incorrectly\n"
        "- User unable to cancel Wix subscription/plan\n"
        "- User having billing disputes with Wix\n"
        "- Domain connection/management/purchase problems through Wix\n"
        "- Google Workspace integration/purchase issues through Wix\n"
        "\n❌ IMMEDIATELY EXCLUDE - DO NOT CLASSIFY AS COMPLAINTS:\n"
        "\n**WEBSITE TECHNICAL ISSUES (NOT BILLING):**\n"
        "- Site won't load, jumps to other pages, redirects incorrectly\n"
        "- Homepage redirecting to Google search\n"
        "- Website display problems, mobile issues\n"
        "- Site speed, performance, or loading issues\n"
        "- Editor problems, design tool issues\n"
        "\n**CUSTOMER PAYMENT FUNCTIONALITY (NOT USER PAYING WIX):**\n"
        "- ANY mention of 'checkout', 'express checkout', 'fast checkout'\n"
        "- Wix Bookings payment setup for services\n"
        "- Wix Stores payment methods for products  \n"
        "- Customer payment processing issues\n"
        "- PayPal, Stripe, or other payment provider setup\n"
        "\n**USER GETTING PAID (NOT USER PAYING WIX):**\n"
        "- Payment verification, payouts, withdrawals\n"
        "- 'How can I get my money', account verification\n"
        "- Receiving payments from customers\n"
        "\n**FREELANCER/BUSINESS RELATIONSHIPS:**\n"
        "- Designer worried about client payments\n"
        "- Client payment requests or disputes\n"
        "\n**WEBSITE FEATURES & FUNCTIONALITY:**\n"
        "- SEO issues, email marketing\n"
        "- Store management, discounts, coupons, inventory\n"
        "- Any website feature not working properly (EXCEPT domains and Google Workspace)\n"
        "\n**QUESTIONS (NOT COMPLAINTS):**\n"
        "- 'How to' questions about any topic\n"
        "- Asking for advice or guidance\n"
        "\n🔥 KEYWORD AUTO-EXCLUDE: If the post contains ANY of these terms, automatically return is_complaint: false\n"
        "- 'checkout', 'express checkout', 'fast checkout'\n"
        "- 'jumps to', 'redirects to', 'won't load'\n"
        "- 'payout', 'get my money', 'payment verification'\n"
        "- 'client payment', 'how to', 'advice'\n"
        "\nEXAMPLES:\n"
        "\n✅ VALID COMPLAINTS (classify as true):\n"
        "Input: 'Wix charged me $50 after I canceled my premium plan last month'\n"
        "Output: {\"is_complaint\": true, \"product_area\": \"billing\", \"summary\": \"User charged after canceling premium plan\", \"urgency\": \"high\"}\n"
        "\nInput: 'Cannot cancel my Wix subscription, the cancel button is broken'\n"
        "Output: {\"is_complaint\": true, \"product_area\": \"subscriptions\", \"summary\": \"User unable to cancel Wix subscription\", \"urgency\": \"high\"}\n"
        "\nInput: 'My domain won't connect to my Wix site, getting errors'\n"
        "Output: {\"is_complaint\": true, \"product_area\": \"domains\", \"summary\": \"User having domain connection issues with Wix\", \"urgency\": \"medium\"}\n"
        "\nInput: 'Google Workspace integration failing through Wix'\n"
        "Output: {\"is_complaint\": true, \"product_area\": \"google_workspace\", \"summary\": \"User experiencing Google Workspace integration issues\", \"urgency\": \"medium\"}\n"
        "\n❌ INVALID - EXCLUDE (classify as false):\n"
        "Input: 'My homepage jumps to Google search instead of staying on my site'\n"
        "Output: {\"is_complaint\": false, \"product_area\": null, \"summary\": null, \"urgency\": null}\n"
        "\nInput: 'Wix express checkout not working on my store'\n"
        "Output: {\"is_complaint\": false, \"product_area\": null, \"summary\": null, \"urgency\": null}\n"
        "\nInput: 'How can I get my money from Wix Payments?'\n"
        "Output: {\"is_complaint\": false, \"product_area\": null, \"summary\": null, \"urgency\": null}\n"
        "\nInput: 'Can't choose payment methods in Wix Bookings'\n"
        "Output: {\"is_complaint\": false, \"product_area\": null, \"summary\": null, \"urgency\": null}\n"
        "\nInput: 'My website won't load properly'\n"
        "Output: {\"is_complaint\": false, \"product_area\": null, \"summary\": null, \"urgency\": null}\n"
        "\nREMEMBER: You are looking for complaints about Wix's billing, subscriptions, domains, and Google Workspace services. Everything else should be classified as false.\n"
        "\nNow, classify this post:\n\nPost:\n" + text
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        # Try to extract JSON from the response
        try:
            # Find the first and last curly braces to extract JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            return json.loads(json_str)
        except Exception:
            return {
                "is_complaint": False,
                "product_area": None,
                "summary": None,
                "urgency": None
            }
    except Exception as e:
        return {
            "is_complaint": False,
            "product_area": None,
            "summary": f"OpenAI error: {e}",
            "urgency": None
        }

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

def write_complaints_to_file(complaints, all_mentions, run_time):
    output_lines = []
    output_lines.append(f"=== Run at {run_time} ===\n")
    output_lines.append(f"Reddit Query: {KEYWORDS}\n")
    output_lines.append(f"Number of posts returned by Reddit API: {len(all_mentions)}\n")
    output_lines.append(f"Titles of posts returned by Reddit API:\n")
    for mention in all_mentions:
        output_lines.append(f"- {mention['title']}\n")
    output_lines.append(f"Number of complaints found: {len(complaints)}\n")
    output_lines.append(f"\nComplaints (with product area, urgency, and summary):\n")
    for complaint in complaints:
        output_lines.append(
            f"- Link: {complaint['link']}\n  Title: {complaint['title']}\n  Date: {complaint['date']}\n  Product Area: {complaint.get('product_area')}\n  Urgency: {complaint.get('urgency')}\n  Complaint Summary: {complaint.get('summary')}\n"
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
        result = is_complaint(mention['title'] + '\n' + mention['text'])
        if result.get("is_complaint"):
            complaints.append({
                "link": mention['link'],
                "title": mention['title'],
                "date": mention['created_date'],
                "product_area": result.get("product_area"),
                "summary": result.get("summary"),
                "urgency": result.get("urgency")
            })
    return complaints, mentions

if __name__ == "__main__":
    run_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    complaints, mentions = get_categorized_complaints(limit=50)
    write_complaints_to_file(complaints, mentions, run_time) 