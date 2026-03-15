# check_login.py
from app import app

print("=" * 60)
print("LOGIN ENDPOINT DIAGNOSTIC")
print("=" * 60)

# Check all routes
print("\n📋 ALL REGISTERED ROUTES:")
print("-" * 40)
for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
    methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
    print(f"{rule.endpoint:30} {rule} [{methods}]")

# Check specifically for login-related routes
print("\n🔍 LOGIN-RELATED ROUTES:")
print("-" * 40)
login_routes = [rule for rule in app.url_map.iter_rules() 
                if 'login' in str(rule).lower() or 'auth' in str(rule).lower()]
if login_routes:
    for rule in login_routes:
        print(f"✅ {rule.endpoint:30} {rule}")
else:
    print("❌ No login-related routes found!")

# Check blueprint registration
print("\n📦 REGISTERED BLUEPRINTS:")
print("-" * 40)
if app.blueprints:
    for name, blueprint in app.blueprints.items():
        print(f"✅ {name}: {blueprint}")
else:
    print("❌ No blueprints registered!")

print("\n" + "=" * 60)
print(f"Template folder: {app.template_folder}")
print(f"Static folder: {app.static_folder}")
print("=" * 60)