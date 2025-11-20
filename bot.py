import os
import feedparser
import requests
import random
from serpapi.google_search import GoogleSearch
from atproto import Client as BskyClient
from google import generativeai as genai
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

# -----------------------------
# Disable CrewAI fallback LLMs completely
# -----------------------------
os.environ["OPENAI_API_KEY"] = ""
os.environ["CREWAI_NATIVE_LLM"] = "disabled"
os.environ["CREWAI_ALLOW_FALLBACK"] = "false"

# ===============================
# ENVIRONMENT VARIABLES
# ===============================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

# ===============================
# GEMINI CONFIG
# ===============================
genai.configure(api_key=GEMINI_API_KEY)

# ===============================
# BLUESKY CLIENT
# ===============================
bsky = BskyClient()
bsky.login(BSKY_HANDLE, BSKY_PASSWORD)

POSTED_NEWS_FILE = "posted_news.txt"

# ===============================
# NEWS STORAGE HELPERS
# ===============================
def load_posted_news():
    if os.path.exists(POSTED_NEWS_FILE):
        with open(POSTED_NEWS_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_posted_news(news_id):
    with open(POSTED_NEWS_FILE, "a") as f:
        f.write(news_id + "\n")


# ===============================
# RSS FEEDS
# ===============================
RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
]


# ===============================
# GET LATEST NEWS (RANDOM PICK)
# ===============================
def get_latest_news():
    articles = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            articles += feed.entries

    if articles:
        article = random.choice(articles)
        return {
            "title": article.title,
            "link": article.link,
            "summary": getattr(article, "summary", "")
        }

    return None


# ===============================
# GENERATE NEWS POST USING GEMINI
# ===============================
def generate_bluesky_post(article):
    prompt = f"""
    Write a short Bluesky post summarizing this news in a breaking-news tone:
    Title: {article['title']}
    Link: {article['link']}
    Summary: {article['summary']}

    Include relevant hashtags and keep it under 300 characters.
    """

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini Error:", e)
        return None


# ===============================
# SERP API IMAGE FETCH
# ===============================
def fetch_news_image(query):
    try:
        params = {
            "engine": "google_images",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 1,
            "safe": "active"
        }
        results = GoogleSearch(params).get_dict()

        if "images_results" in results and len(results["images_results"]) > 0:
            return results["images_results"][0]["original"]
        return None

    except Exception as e:
        print(f"Error fetching image: {e}")
        return None


# ===============================
# POST IMAGE TO BLUESKY
# ===============================
def post_image_to_bluesky(text, image_url):
    try:
        # Download image
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        img_data = img_response.content
        
        # Upload image
        upload = bsky.com.atproto.repo.upload_blob(data=img_data)
        
        # Create post with image embed
        post = bsky.send_post(
            text=text,
            embed={
                "$type": "app.bsky.embed.images",
                "images": [{
                    "image": {
                        "$type": "blob",
                        "ref": {"$link": upload.blob.ref.link},  # <== FIXED
                        "mimeType": "image/jpeg",
                        "size": len(img_data),
                    },
                    "alt": "Relevant news image",
                }],
            }
        )
        
        print(f"🎉 Posted with image! URI: {post.uri}")
        
    except Exception as e:
        print(f"❌ Error posting with image: {e}")


# ===========================================================
# CREWAI (NO LLM) — EXACT SAME STRUCTURE AS YOUR SAMPLE CODE
# ===========================================================
from crewai import Agent, Task, Crew

news_agent = Agent(
    role="News Coordinator",
    goal="Coordinate fetching and selecting news.",
    llm=None,  # ❌ NO LLM
    allow_delegation=False,
    max_iter=1,
    use_executor=False,
    backstory="Handles orchestration only."
)

post_agent = Agent(
    role="Post Builder",
    goal="Coordinate summarizing and image fetching.",
    llm=None,  # ❌ NO LLM
    allow_delegation=False,
    max_iter=1,
    use_executor=False,
    backstory="Supervises Gemini + SerpAPI tasks only."
)

upload_agent = Agent(
    role="Upload Coordinator",
    goal="Coordinate Bluesky uploading.",
    llm=None,  # ❌ NO LLM
    allow_delegation=False,
    max_iter=1,
    use_executor=False,
    backstory="Handles orchestration of posting."
)

fetch_task = Task(
    description="Organize the news fetching.",
    expected_output="News fetched.",
    agent=news_agent
)

build_task = Task(
    description="Organize summarizing and image retrieval.",
    expected_output="Post content ready.",
    agent=post_agent
)

upload_task = Task(
    description="Organize posting to Bluesky.",
    expected_output="Post uploaded.",
    agent=upload_agent
)

# Dummy crew (NO kickoff → NO LLM)
crew = Crew(
    agents=[news_agent, post_agent, upload_agent],
    tasks=[fetch_task, build_task, upload_task],
    verbose=False
)

def run_crew_workflow():
    return "CrewAI workflow started (no LLM used)."


# ===============================
# MAIN BOT WORKFLOW
# ===============================
def run_bluesky_news_bot():
    print(run_crew_workflow())   # CrewAI orchestrator
    print("🗞 Fetching news...")

    article = get_latest_news()
    if not article:
        print("❌ No news found.")
        return

    news_id = article["link"]
    posted_news = load_posted_news()

    if news_id in posted_news:
        print(f"🔄 Already posted: “{news_id}” — Skipping...")
        return

    print(f"🔥 New headline detected: {article['title']}")

    post_text = generate_bluesky_post(article)
    if not post_text:
        print("❌ Failed to generate content.")
        return

    print("\n📝 Post Content:")
    print(post_text)

    print("\n🔍 Fetching image...")
    image_url = fetch_news_image(article["title"])

    print("\n📤 Posting to Bluesky...")
    if image_url:
        post_image_to_bluesky(post_text, image_url)
    else:
        bsky.send_post(post_text)
        print("📄 Posted text-only.")

    save_posted_news(news_id)


# ===============================
# SCHEDULER
# ===============================
import time
from threading import Thread, Event

stop_scheduler = Event()

def schedule_custom_interval(interval_minutes):
    stop_scheduler.clear()
    print(f"⏱️ Scheduler started (every {interval_minutes} minutes).")

    def scheduler():
        while not stop_scheduler.is_set():
            run_bluesky_news_bot()
            time.sleep(interval_minutes * 60)

    Thread(target=scheduler, daemon=True).start()

def stop_schedule():
    stop_scheduler.set()
    print("🛑 Scheduler stopped.")


if __name__ == "__main__":
    pass
