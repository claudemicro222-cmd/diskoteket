"""Konstanter för Diskoteket-integrationen."""
from datetime import timedelta

DOMAIN = "diskoteket"
VERSION = "4.2.0"
CONF_API_KEY = "api_key"
SCAN_INTERVAL = timedelta(minutes=10)
CARD_URL = "/diskoteket_card/diskoteket-card.js"
