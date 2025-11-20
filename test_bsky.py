# test_bsky.py
import os
from dotenv import load_dotenv
from atproto import Client         # if you used `from atproto import Client as BskyClient` in bot.py

load_dotenv()
handle = os.getenv("BSKY_HANDLE")
pw = os.getenv("BSKY_PASSWORD")

print("HANDLE:", handle)
print("PASSWORD LENGTH:", len(pw))

c = Client()
try:
    resp = c.login(handle, pw)
    print("LOGIN OK:", resp)
except Exception as e:
    print("LOGIN FAILED:", type(e), e)
    raise

# Try a simple text post test
try:
    p = c.send_post(text="Test post from bot at " + handle)
    print("POST OK:", p)
except Exception as e:
    print("POST FAILED:", type(e), e)
    raise
