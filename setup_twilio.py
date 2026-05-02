#!/usr/bin/env python3
"""
Quick Twilio Setup Script
This script helps you configure Twilio for real SMS OTP delivery
"""

print("="*70)
print("📱 TWILIO SMS SETUP FOR REAL-TIME OTP DELIVERY")
print("="*70)
print()

# Check if twilio is installed
try:
    import twilio
    print("✅ Twilio library is installed")
except ImportError:
    print("❌ Twilio library not found")
    print("   Installing Twilio...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "twilio"])
    print("✅ Twilio installed successfully!")
    print()

print("="*70)
print("STEP 1: Get Your Twilio Credentials")
print("="*70)
print()
print("1. Sign up at: https://www.twilio.com/try-twilio (FREE trial)")
print("2. After signing up, go to your Twilio Console Dashboard")
print("3. You'll need:")
print("   - Account SID (starts with 'AC')")
print("   - Auth Token (click 'View' to reveal)")
print("   - Phone Number (get a free trial number)")
print()

# Get credentials from user
print("="*70)
print("STEP 2: Enter Your Twilio Credentials")
print("="*70)
print()

account_sid = input("Enter your Twilio Account SID: ").strip()
auth_token = input("Enter your Twilio Auth Token: ").strip()
from_number = input("Enter your Twilio Phone Number (with +): ").strip()

if not account_sid or not auth_token or not from_number:
    print("\n❌ All fields are required!")
    exit(1)

# Validate format
if not account_sid.startswith('AC'):
    print("\n⚠️  Warning: Account SID should start with 'AC'")
    
if not from_number.startswith('+'):
    print("\n⚠️  Warning: Phone number should start with '+' (e.g., +14155552671)")

# Update otp_config.py
print()
print("="*70)
print("STEP 3: Updating otp_config.py")
print("="*70)
print()

try:
    with open('otp_config.py', 'r') as f:
        content = f.read()
    
    # Replace the SMS_CONFIG section
    import re
    
    new_config = f"""SMS_CONFIG = {{
    'enabled': True,  # Set to True to enable real SMS sending
    'account_sid': '{account_sid}',
    'auth_token': '{auth_token}',
    'from_number': '{from_number}',  # Your Twilio phone number
    'service_name': 'Hospital OTP Service'
}}"""
    
    # Replace the SMS_CONFIG block
    pattern = r"SMS_CONFIG = \{.*?\}"
    content = re.sub(pattern, new_config, content, flags=re.DOTALL)
    
    with open('otp_config.py', 'w') as f:
        f.write(content)
    
    print("✅ otp_config.py updated successfully!")
    print()
    
except Exception as e:
    print(f"❌ Error updating otp_config.py: {e}")
    print("   Please update it manually:")
    print()
    print("   SMS_CONFIG = {")
    print(f"       'enabled': True,")
    print(f"       'account_sid': '{account_sid}',")
    print(f"       'auth_token': '{auth_token}',")
    print(f"       'from_number': '{from_number}',")
    print(f"       'service_name': 'Hospital OTP Service'")
    print("   }")
    exit(1)

# Test connection
print("="*70)
print("STEP 4: Testing Twilio Connection")
print("="*70)
print()

try:
    from twilio.rest import Client
    client = Client(account_sid, auth_token)
    
    # Try to fetch account info
    account = client.api.accounts(account_sid).fetch()
    print(f"✅ Connected to Twilio!")
    print(f"   Account Name: {account.friendly_name}")
    print(f"   Status: {account.status}")
    print()
    
except Exception as e:
    print(f"❌ Connection test failed: {e}")
    print("   Please check your credentials and try again")
    exit(1)

print("="*70)
print("✅ SETUP COMPLETE!")
print("="*70)
print()
print("📱 Real SMS OTP is now enabled!")
print()
print("⚠️  IMPORTANT FOR TRIAL ACCOUNTS:")
print("   - You can only send SMS to VERIFIED phone numbers")
print("   - Go to Twilio Console → Phone Numbers → Verified Caller IDs")
print("   - Add and verify the phone numbers you want to test with")
print()
print("🚀 Next Steps:")
print("   1. Restart your Flask application")
print("   2. Try registering/login with a verified phone number")
print("   3. Check your phone for the OTP SMS!")
print()
print("="*70)
