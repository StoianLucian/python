import os
from repositories.aiChat_repository import initialize_model_generate, return_available_models
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from prompts.prompts import slack_bot_prompt
import json

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

    client.reactions_add(
        channel=event["channel"],
        timestamp=event["ts"],
        name="robot_face"
    )

    history = client.conversations_history(channel=slack_chanel, limit=10)

    chanel_history = [
        {
            "user": h["user"],
            "content": h["text"]
        }
        for h in history["messages"]
    ]

    message = {
        "user": slack_user,
        "content": slack_content
    }

    models = return_available_models()

    print(models[0]["id"])

    availableModel = models[0]["id"]

    slack_prompt = slack_bot_prompt.format(
        user_prompt=message, user=slack_user, chanel_history=chanel_history)

    reponse_summary = initialize_model_generate(
        availableModel, slack_prompt)

    response = reponse_summary.get('response')

    say(f"{response}")


@slack_app.event("message")
def handle_message(event, say, client):

    if event.get("channel_type") != "channel":
        return

    if event.get("bot_id"):
        return

    slack_content = event["text"]
    slack_user = event["user"]
    slack_chanel = event["channel"]

    history = client.conversations_history(channel=slack_chanel, limit=10)

    chanel_history = [
        {
            "user": h["user"],
            "content": h["text"]
        }
        for h in history["messages"]
    ]

    message = {
        "user": slack_user,
        "content": slack_content
    }

    models = return_available_models()

    print(models[0]["id"])

    availableModel = models[0]["id"]

    slack_prompt = slack_bot_prompt.format(
        user_prompt=message, user=slack_user, chanel_history=chanel_history)

    reponse_summary = initialize_model_generate(
        availableModel, slack_prompt)

    response = reponse_summary.get('response')

    say(f"{response}")
