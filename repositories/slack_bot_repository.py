
import logging

from repositories.aiChat_repository import initialize_model_generate, return_available_models
from prompts.prompts import slack_bot_prompt
from slack_sdk.errors import SlackApiError


def return_slack_response(slack_message, slack_user: str, history):

    try:
        models = return_available_models()
        availableModel = models[0]["id"]

        chanel_history = [
            {
                "user": h["user"],
                "content": h["text"]
            }
            for h in history["messages"]
        ]

        message = {
            "user": slack_user,
            "content": slack_message
        }

        slack_prompt = slack_bot_prompt.format(
            user_prompt=message, user=slack_user, chanel_history=chanel_history)

        reponse_summary = initialize_model_generate(
            availableModel, slack_prompt)

        response = reponse_summary.get('response')

    except SlackApiError as e:
        logging.info('slack_bot_repository.return_slack_response')
        print(f"error accessing slack bot {e}")
        return "error accessing slack bot"

    return response


def handle_reaction(client, event, add=True, emojis=None):

    if emojis is None:
        emojis = ["robot_face"]

    action = getattr(client, "reactions_add" if add else "reactions_remove")

    for emoji in emojis:
        try:
            action(
                channel=event["channel"],
                timestamp=event["ts"],
                name=emoji
            )
        except Exception as e:
            print(f"Failed to add {emoji}: {e}")


def is_tag_message(id, content):
    if f"<@{id}>" in content:
        return True
    else:
        return False
