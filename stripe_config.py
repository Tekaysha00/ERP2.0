import stripe
import os

from dotenv import load_dotenv

load_dotenv()

STRIPE_PUBLISHABLE_KEY = os.getenv(
    "STRIPE_PUBLISHABLE_KEY"
)

STRIPE_SECRET_KEY = os.getenv(
    "STRIPE_SECRET_KEY"
)

stripe.api_key = STRIPE_SECRET_KEY