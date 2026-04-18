# scripts/list_routes.py
import os, sys

# determine project root (one level up from this scripts folder)
this_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(this_file))
sys.path.insert(0, project_root)

try:
    from app import create_app
except Exception as e:
    print("ERROR importing create_app():", e)
    raise

app = create_app()

with app.app_context():
    rules = sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, r.endpoint))
    for r in rules:
        methods = ','.join(sorted([m for m in r.methods if m not in ('HEAD','OPTIONS')]))
        print(f"{methods:8} {r.rule:35} -> {r.endpoint}")