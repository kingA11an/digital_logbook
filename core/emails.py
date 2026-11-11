import os 
import resend 

resend.api_key = os.environ.get('RESEND_API_KEY')

def send_resend_email(to_email, subject, body_text):
    """
    Utility function to send emails via Resend HTTP API.
    Bypasses blocked SMTP ports on cloud hosts like Render 
    """
    if not resend.api_key:
        raise ValueError("RESEND_API_KEY environment variable is not set.")
    
    params = {
        # Resend provides 'onboarding@resend.dev' for testing without domain verification 
        "from": "TrueLog Support <onboarding@resend.dev>",
        "to": [to_email],
        "subject": subject,
        "text": body_text,
    }
    
    response = resend.Emails.send(params)
    return response