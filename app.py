import streamlit as st
from io import StringIO
from contextlib import redirect_stdout

# Import functions from your bot.py
from bot import (
    run_bluesky_news_bot,
    load_posted_news,
    get_latest_news,
    generate_bluesky_post,
    fetch_news_image,
    schedule_custom_interval,
    stop_schedule
)

# ===============================
# STREAMLIT PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Bluesky News Bot",
    page_icon="📰",
    layout="centered"
)

st.title("📰 Bluesky Breaking News Bot")
st.write(
    "This bot fetches the latest headline, summarizes with Gemini, "
    "gets an image using SerpAPI, and posts it to Bluesky automatically."
)

st.divider()


# ===============================
# FUNCTION: Capture Bot Logs
# ===============================
def capture_logs(func):
    buffer = StringIO()
    with redirect_stdout(buffer):
        func()
    return buffer.getvalue()


# ===============================
# PREVIEW SECTION
# ===============================
st.subheader("🔍 Preview Next News Post (No Posting)")

if st.button("Fetch Latest News Preview"):
    article = get_latest_news()

    if not article:
        st.error("No news found.")
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

            with st.spinner("Searching image..."):
                img_url = fetch_news_image(article["title"])

            if img_url:
                st.write("### 🖼 Image Preview")
                st.image(img_url, caption="Top SerpAPI Image", use_container_width=True)
            else:
                st.info("No image found.")
        else:
            st.error("Gemini failed to generate summary.")

st.divider()


# ===============================
# RUN BOT + SHOW LOGS
# ===============================
st.subheader("🚀 Run Bot and Post to Bluesky")

if st.button("Run Bot Now"):
    st.info("Running bot... please wait ⏳")

    with st.spinner("Posting to Bluesky..."):
        logs = capture_logs(run_bluesky_news_bot)

    st.success("Bot run completed!")

    st.write("### 📜 Run Logs")
    st.code(logs)


st.divider()


# ===============================
# POSTED NEWS HISTORY
# ===============================
st.subheader("🧾 Posted Headlines")

if st.button("Refresh History"):
    posted = load_posted_news()
    if posted:
        st.write(f"Total: **{len(posted)}**")
        for title in posted:
            st.write("- ", title)
    else:
        st.info("No posts yet.")

st.divider()


# ===============================
# AUTO-SCHEDULER
# ===============================
st.subheader("⏱️ Auto Posting Scheduler")

interval = st.number_input(
    "Interval (minutes):",
    min_value=1,
    max_value=360,
    value=60
)

if "scheduler_running" not in st.session_state:
    st.session_state.scheduler_running = False

if not st.session_state.scheduler_running:
    if st.button("Start Scheduler"):
        stop_schedule()
        schedule_custom_interval(interval)
        st.session_state.scheduler_running = True
        st.success(f"Scheduler started — posting every {interval} minutes.")
else:
    if st.button("Stop Scheduler"):
        stop_schedule()
        st.session_state.scheduler_running = False
        st.warning("Scheduler stopped.")

st.caption("Built with Streamlit + Gemini + SerpAPI + Bluesky API 💙")
