import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'), override=True)
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.authorization.authorize_result import AuthorizeResult
import threading
import time
import requests

# --- Slack App vs Bot ---
# In Slack, an "App" is the overall integration you create in the Slack API dashboard.
# A "Bot" is a user-like entity (with a bot token) that acts on behalf of the app.
# You can have a bot user in your app, and you can invite it to channels, DM it, etc.
# You can also create a dedicated channel (e.g., #uni-bot) for conversations with the bot.

# --- Environment Variables ---
# SLACK_BOT_REFRESH_TOKEN: Used to programmatically fetch the bot access token (if needed)
# SLACK_BOT_ACCESS_TOKEN: The bot access token (xoxb-... or xoxe-...)
# SLACK_SOCKET_APP_TOKEN: The app-level token for Socket Mode (xapp-...)

SLACK_BOT_REFRESH_TOKEN = os.environ.get("SLACK_BOT_REFRESH_TOKEN")
SLACK_BOT_ACCESS_TOKEN = os.environ.get("SLACK_BOT_ACCESS_TOKEN")
SLACK_SOCKET_APP_TOKEN = os.environ.get("SLACK_SOCKET_APP_TOKEN")

print("[SlackBot] Loaded environment variables:")
if SLACK_BOT_ACCESS_TOKEN:
    print(f"  SLACK_BOT_ACCESS_TOKEN: {SLACK_BOT_ACCESS_TOKEN[:12]}...{SLACK_BOT_ACCESS_TOKEN[-8:]}")
else:
    print("  SLACK_BOT_ACCESS_TOKEN: None")
if SLACK_SOCKET_APP_TOKEN:
    print(f"  SLACK_SOCKET_APP_TOKEN: {SLACK_SOCKET_APP_TOKEN[:12]}...{SLACK_SOCKET_APP_TOKEN[-8:]}")
else:
    print("  SLACK_SOCKET_APP_TOKEN: None")

# If you want to fetch the bot token using a refresh token, implement here:
def fetch_bot_token(refresh_token):
    # TODO: Implement the OAuth token refresh flow if needed
    # For now, just return the existing bot access token
    return SLACK_BOT_ACCESS_TOKEN

if not SLACK_BOT_ACCESS_TOKEN and SLACK_BOT_REFRESH_TOKEN:
    SLACK_BOT_ACCESS_TOKEN = fetch_bot_token(SLACK_BOT_REFRESH_TOKEN)

if not SLACK_BOT_ACCESS_TOKEN or not SLACK_SOCKET_APP_TOKEN:
    raise RuntimeError("SLACK_BOT_ACCESS_TOKEN (or refresh flow) and SLACK_SOCKET_APP_TOKEN must be set in your environment.")

# --- Modern Slack App: Use authorize callback ---
def authorize_func(client, body=None, **kwargs):
    if body is None:
        body = {}
    return AuthorizeResult(
        bot_token=SLACK_BOT_ACCESS_TOKEN,
        user_id=body.get("user_id"),
        team_id=body.get("team_id"),
        enterprise_id=None,
    )

app = App(authorize=authorize_func)

# --- Message Event Handler ---
@app.event("message")
def handle_message_events(body, say, event, logger):
    user = event.get("user")
    text = event.get("text")
    channel = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")
    subtype = event.get("subtype")
    bot_user_id = body.get("authorizations", [{}])[0].get("user_id")
    print(f"[SlackBot] Received message event: user={user}, channel={channel}, text={text}, thread_ts={thread_ts}, subtype={subtype}")
    # Ignore messages from the bot itself or with a subtype (e.g., bot_message, message_changed)
    if subtype is not None:
        print(f"[SlackBot] Ignored message with subtype: {subtype}")
        return
    if user == bot_user_id:
        print(f"[SlackBot] Ignored message from self (bot user_id: {bot_user_id})")
        return
    # Call FastAPI backend asynchronously (no immediate reply)
    def async_backend():
        try:
            backend_response = requests.post(
                "http://localhost:8000/prompt",
                json={"prompt": text, "user_id": user},
                timeout=30
            )
            print(f"[SlackBot] Backend /prompt response: {backend_response.status_code} {backend_response.text}")
            if backend_response.ok:
                data = backend_response.json()
                result = data.get("message", "(No response)")
            else:
                result = "Sorry, there was an error fetching the result."
        except Exception as e:
            result = f"Error: {e}"
        say(text=result, thread_ts=thread_ts)
        print(f"[SlackBot] Sent final result reply to channel={channel}, thread_ts={thread_ts}")
    threading.Thread(target=async_backend).start()

# --- /uni Slash Command Handler ---
@app.command("/uni")
def handle_uni_command(ack, respond, command, logger):
    ack()
    user = command["user_id"]
    text = command["text"]
    channel = command["channel_id"]
    print(f"[SlackBot] Received /uni slash command: user={user}, channel={channel}, text={text}")
    # Call FastAPI backend asynchronously (no immediate reply)
    def async_backend():
        try:
            backend_response = requests.post(
                "http://localhost:8000/prompt",
                json={"prompt": text, "user_id": user},
                timeout=30
            )
            print(f"[SlackBot] Backend /prompt response: {backend_response.status_code} {backend_response.text}")
            if backend_response.ok:
                data = backend_response.json()
                result = data.get("message", "(No response)")
            else:
                result = "Sorry, there was an error fetching the result."
        except Exception as e:
            result = f"Error: {e}"
        respond(result)
        print(f"[SlackBot] Sent final slash command result reply to channel={channel}")
    threading.Thread(target=async_backend).start()

# --- Dedicated Channel Support ---
# To use a dedicated channel, invite the bot to that channel in Slack (e.g., #uni-bot).
# Users can then mention the bot or use /uni in that channel.

if __name__ == "__main__":
    print("[SlackBot] Starting Slack bot in Socket Mode...")
    print("[SlackBot] To test: In Slack, DM the bot, mention it in a channel, or use /uni in a channel where the bot is present.")
    handler = SocketModeHandler(app, SLACK_SOCKET_APP_TOKEN)
    handler.start() 