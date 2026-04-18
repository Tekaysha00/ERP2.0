# scripts/check_endpoints.py
import os, sys, requests, json, time

this_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(this_file))
sys.path.insert(0, project_root)

BASE = "http://127.0.0.1:5000"

# Adjust these to your real login route & placeholder credentials:
LOGIN_PATH = "/api/users/login2"   # update if your login endpoint differs
LOGIN_ADMIN = {"phone": "9999999999", "dob": "2000-01-01"}  # change

def get_token():
    url = BASE + LOGIN_PATH
    r = requests.post(url, json=LOGIN_ADMIN, timeout=6)
    print("LOGIN ->", r.status_code, r.text[:200])
    if r.status_code == 200:
        j = r.json()
        # try common token keys:
        return j.get("access_token") or j.get("token") or j.get("access")
    return None

def check(endpoints, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for method, path, payload in endpoints:
        url = BASE + path
        try:
            r = requests.request(method, url, json=payload, headers=headers, timeout=8)
            print(f"{method:6} {path:35} -> {r.status_code}")
            # print a short body preview
            t = r.text[:300].replace("\n", " ")
            print("   ", t)
        except Exception as e:
            print(f"{method:6} {path:35} -> ERROR: {e}")

if __name__ == "__main__":
    # list endpoints to test (edit these)
    endpoints = [
        ("GET", "/api/test", None),
        ("GET", "/api/classes/list", None),
        # add protected endpoints after you inspect the route list
        # ("GET", "/api/students/register-form", None),
    ]

    token = get_token()
    check(endpoints, token)