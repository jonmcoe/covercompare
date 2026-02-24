import datetime
import json
import os
import requests

def post(path, current_date, extra_text="", webhook_url=None, username=None):

    if webhook_url is None:
        webhook_url = os.environ.get('COVERCOMPARE_DISCORD_WEBHOOK')

    formatted_date = current_date.strftime("%A, %B %d %Y")

    # Open the image file in binary mode
    with open(path, "rb") as f:
        files = {
            "file": ("image.jpg", f)
        }
        msg = {"content": extra_text + formatted_date,
               "embeds": [{"image": {"url": "attachment://image.jpg"}}]}
        if username:
            msg["username"] = username
        payload = {
            "payload_json": json.dumps(msg)
        }
        response = requests.post(webhook_url, data=payload, files=files)
        return response