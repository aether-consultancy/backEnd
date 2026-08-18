import os
import secrets
import string
import requests

VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_TTL_MINUTES = 15
VERIFICATION_CODE_ALPHABET = string.ascii_uppercase + string.digits

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "no-reply@eduway.app")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "Eduway")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def generate_verification_code() -> str:
    return "".join(secrets.choice(VERIFICATION_CODE_ALPHABET) for _ in range(VERIFICATION_CODE_LENGTH))


def send_code_email(to_email: str, code: str, purpose: str = "verification") -> bool:
    if not BREVO_API_KEY:
        return False

    subject = "Verify your Eduway email" if purpose == "verification" else "Reset your Eduway password"
    body = f"<p>Your code is: <strong>{code}</strong></p><p>This code expires in {VERIFICATION_CODE_TTL_MINUTES} minutes.</p>"

    payload = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": body,
    }
    headers = {"api-key": BREVO_API_KEY, "Content-Type": "application/json"}

    response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
    return response.status_code in (200, 201)
