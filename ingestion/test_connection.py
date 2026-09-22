import os
from dotenv import load_dotenv
import requests

load_dotenv()

token = os.getenv("ENTSOE_API_TOKEN")

if not token:
    raise ValueError("ENTSOE_API_TOKEN not found")

url = "https://web-api.tp.entsoe.eu/api"

params = {
    "securityToken": token,
    "documentType": "A44",
    "in_Domain": "10Y1001A1001A73I",
    "out_Domain": "10Y1001A1001A73I",
    "periodStart": "202609200000",
    "periodEnd": "202609210000"
}

response = requests.get(url, params=params, timeout=30)

print("Status:", response.status_code)
print("Length:", len(response.text))
print(response.text[:2000])