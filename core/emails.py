import os
import requests

def send_brevo_email(to_email, subject, body_text):
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise ValueError("BREVO_API_KEY environment variable is not set.")
    
    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    payload = {
        "sender": {"name": "TrueLog Support", "email": "truelog.support@gmail.com"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body_text
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()