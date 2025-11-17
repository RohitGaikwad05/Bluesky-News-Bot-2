import streamlit as st

# Import functions from your bot.py
from bot import (
    run_bluesky_news_bot,
    load_posted_news,
    get_latest_news,
    generate_bluesky_post,
    fetch_news_image,
)

st.set_page_config(
    page_title="Bluesky News Bot",
    page_icon="📰",
    layout="centered"
)

st.title("📰 Bluesky Breaking News Bot")
st.write(
    "This app fetches the latest headline, summarizes it with Gemini, "
    "gets an image via SerpAPI, and posts to your Bluesky account."
)

st.divider()

# --- Section: Preview next post (no posting) ---
st.subheader("🔍 Preview Next News Post (won't publish)")

if st.button("Fetch Latest News Preview"):
    article = get_latest_news()
    if not article:
        st.error("No news found from RSS feed.")
    else:
        st.write("**Headline:**", article["title"])
        st.write("**Link:**", article["link"])
        if article["summary"]:
            st.write("**Summary:**")
            st.write(article["summary"])

        with st.spinner("Generating Gemini summary..."):
            preview_post = generate_bluesky_post(article)

        if preview_post:
            st.write("### 📝 Generated Post Text")
            st.write(preview_post)

            with st.spinner("Searching image with SerpAPI..."):
                img_url = fetch_news_image(article["title"])

            if img_url:
                st.write("### 🖼 Image Preview")
                st.image(img_url, caption="Top SerpAPI Image", use_container_width=True)
            else:
                st.info("No image found for this headline.")
        else:
            st.error("Gemini failed to generate content.")

st.divider()

# --- Section: Run bot and actually post ---
st.subheader("🚀 Run Bot and Post to Bluesky")

if st.button("Run Bot Now (Post Latest News)"):
    with st.spinner("Running bot, posting to Bluesky..."):
        run_bluesky_news_bot()
    st.success("✅ Bot run finished. Check your Bluesky profile.")

st.divider()

# --- Section: Posted news history ---
st.subheader("🧾 Previously Posted Headlines")

if st.button("Refresh Posted News List"):
    posted = load_posted_news()
    if posted:
        st.write(f"Total posted headlines: **{len(posted)}**")
        for title in posted:
            st.write("- ", title)
    else:
        st.info("No headlines recorded yet (posted_news.txt is empty).")

st.caption("Built with Streamlit + Gemini + SerpAPI + Bluesky API 💙")

st.divider()
st.subheader("⏱️ Auto Post Scheduler")

interval = st.number_input("Schedule Interval (in minutes)", min_value=1, max_value=360, value=60)

# Always ensure that scheduler state is tracked in session
if "scheduler_running" not in st.session_state:
    st.session_state.scheduler_running = False

if not st.session_state.scheduler_running:
    if st.button("Start Scheduler"):
        from bot import schedule_custom_interval, stop_schedule
        
        # Stop any existing scheduler before starting new one
        stop_schedule()
        schedule_custom_interval(interval)
        
        st.session_state.scheduler_running = True
        st.success(f"🟢 Scheduler started: posting every {interval} minutes!")
else:
    if st.button("Stop Scheduler"):
        from bot import stop_schedule
        
        stop_schedule()
        st.session_state.scheduler_running = False
        st.warning("🔴 Scheduler stopped.")
