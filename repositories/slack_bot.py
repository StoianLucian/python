import os
from repositories.slack_bot_repository import handle_reaction, is_tag_message, return_slack_response
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SIGNING_SECRET = os.getenv("SIGNING_SECRET")

slack_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SIGNING_SECRET
)

handler = SlackRequestHandler(slack_app)


@slack_app.event("app_mention")
def handle_mention(event, client, say):
    slack_content = event["text"]
    slack_user = event["user"]
    slack_chanel = event["channel"]

    handle_reaction(client, event)

    history = client.conversations_history(channel=slack_chanel, limit=10)

    response = return_slack_response(slack_content, slack_user, history)

    say(f"{response}")

    handle_reaction(client, event, emojis=["white_check_mark"])


@slack_app.event("message")
def handle_message(event, say, client):

    slack_content = event["text"]
    slack_user = event["user"]
    slack_chanel = event["channel"]
    bot_user_id = client.auth_test()["user_id"]

    if is_tag_message(bot_user_id, slack_content):
        return

    if event.get("channel_type") != "channel":
        return

    handle_reaction(client, event)

    history = client.conversations_history(channel=slack_chanel, limit=10)

    response = return_slack_response(slack_content, slack_user, history)

    say(f"{response}")

    handle_reaction(client, event, emojis=["white_check_mark"])
