import datetime
import json
import os
import requests

def post(path, d=None):

    webhook_url = os.environ.get('COVERCOMPARE_DISCORD_WEBHOOK')

    current_date = d or datetime.datetime.now()
    formatted_date = current_date.strftime("%A, %B %d")

    # Open the image file in binary mode
    with open(path, "rb") as f:
        files = {
            "file": ("image.jpg", f)
        }
        payload = {
            "payload_json": json.dumps({
                "content": formatted_date,
                "embeds": [{"image": {"url": "attachment://image.jpg"}}]
                })
        }
        response = requests.post(webhook_url, data=payload, files=files)
        return response