import os, requests
from dotenv import load_dotenv
load_dotenv()
API = os.getenv("API_URL", "http://127.0.0.1:8000")

def api_get(path, params=None, timeout=10):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_post(path, payload, timeout=15):
    try:
        r = requests.post(f"{API}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)
