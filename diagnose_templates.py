import os
import sys
from flask import Flask

print("=" * 50)
print("TEMPLATE DIAGNOSTIC")
print("=" * 50)

# Check current directory
print(f"\n1. Current directory: {os.getcwd()}")

# Check if web/templates exists
template_path = os.path.join(os.getcwd(), 'web', 'templates')
print(f"\n2. Template path: {template_path}")
print(f"   Exists: {os.path.exists(template_path)}")

if os.path.exists(template_path):
    print(f"\n3. Files in templates folder:")
    for f in os.listdir(template_path):
        full_path = os.path.join(template_path, f)
        size = os.path.getsize(full_path)
        print(f"   - {f} ({size} bytes)")

# Test Flask template loading
print(f"\n4. Testing Flask template loading:")
try:
    app = Flask(__name__, template_folder=template_path)
    print(f"   ✅ Flask initialized with template_folder={app.template_folder}")
    
    # Try to find each template
    templates = ['index.html', 'exam.html', 'proctor_dashboard.html', 'admin.html']
    for template in templates:
        try:
            app.jinja_env.get_template(template)
            print(f"   ✅ Found: {template}")
        except:
            print(f"   ❌ Not found: {template}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 50)