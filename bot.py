import os
import feedparser
import requests
from serpapi import GoogleSearch
from atproto import Client as BskyClient
from google import generativeai as genai
from dotenv import load_dotenv
load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
BSKY_HANDLE = os.getenv("BSKY_HANDLE")
BSKY_PASSWORD = os.getenv("BSKY_PASSWORD")

# Configure APIs
genai.configure(api_key=GEMINI_API_KEY)

bsky = BskyClient()
bsky.login(BSKY_HANDLE, BSKY_PASSWORD)

# Bluesky Client Setup
bsky = BskyClient()
bsky.login(BSKY_HANDLE, BSKY_PASSWORD)

POSTED_NEWS_FILE = "posted_news.txt"

def load_posted_news():
    if os.path.exists(POSTED_NEWS_FILE):
        with open(POSTED_NEWS_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_posted_news(news_id):
    with open(POSTED_NEWS_FILE, "a") as f:
        f.write(news_id + "\n")


RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
]

import random

def get_latest_news():
    articles = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        if feed.entries:
            articles += feed.entries  # add all entries

    if articles:
        article = random.choice(articles)  # pick one at random
        return {
            "title": article.title,
            "link": article.link,
            "summary": getattr(article, 'summary', '')
        }

    return None

    
    # Pick top article
    top_article = feed.entries[0]
    return {
        "title": top_article.title,
        "link": top_article.link,
        "summary": top_article.summary if hasattr(top_article, "summary") else "",
    }
    
def generate_bluesky_post(article):
    prompt = f"""
    Write a short Bluesky post summarizing this news in a breaking-news tone:
    Title: {article['title']}
    Link: {article['link']}
    Summary: {article['summary']}

    Include relevant hashtags and keep it under 300 characters.
    """
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash-preview-05-20")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini Error:", e)
        return None

def fetch_news_image(query):
    try:
        params = {
            "engine": "google_images",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 1,
            "safe": "active"
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "images_results" in results and len(results["images_results"]) > 0:
            return results["images_results"][0]["original"]
        else:
            print("❌ No images found.")
            return None
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None
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

def run_bluesky_news_bot():
    print("🗞 Fetching news...")
    article = get_latest_news()
    if not article:
        print("❌ No news found.")
        return
    
    # Unique identifier for this news item (title used here)
    news_id = article["link"]  # better unique ID
    posted_news = load_posted_news()
    
    if news_id in posted_news:
        print(f"🔄 Already posted: “{news_id}” — Skipping...")
        return
    
    print(f"🔥 New headline detected: {article['title']}")
    
    post_text = generate_bluesky_post(article)
    
    if post_text:
        print("\n📝 Post Content:")
        print(post_text)

        print("\n🔍 Fetching image...")
        image_url = fetch_news_image(article['title'])
        
        print("\n📤 Posting to Bluesky...")
        if image_url:
            post_image_to_bluesky(post_text, image_url)
        else:
            bsky.send_post(post_text)
            print("📄 Posted text-only.")
        
        # Save this news ID to prevent re-posting
        save_posted_news(news_id)
    else:
        print("❌ Failed to generate content.")


import time
from threading import Thread, Event

# Global stopper for schedule
stop_scheduler = Event()

def schedule_custom_interval(interval_minutes):
    """
    Schedule bot to run periodically.
    :param interval_minutes: int - time between runs in minutes
    """
    stop_scheduler.clear()
    print(f"⏱️ Scheduler started (every {interval_minutes} minutes).")

    def scheduler():
        while not stop_scheduler.is_set():
            run_bluesky_news_bot()
            print(f"⏳ Waiting for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)

    Thread(target=scheduler, daemon=True).start()


def stop_schedule():
    """Stop the scheduler gracefully."""
    stop_scheduler.set()
    print("🛑 Scheduler stopped.")

if __name__ == "__main__":
    # For debugging:
    # run_bluesky_news_bot()
    pass

