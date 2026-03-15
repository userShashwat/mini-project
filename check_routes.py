# check_routes.py
from app import app

print("=" * 60)
print("REGISTERED ROUTES")
print("=" * 60)

for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
    print(f"{rule.endpoint:30} {rule}")

print("\n" + "=" * 60)
print(f"Template folder: {app.template_folder}")
print(f"Static folder: {app.static_folder}")
print("=" * 60)