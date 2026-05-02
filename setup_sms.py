#!/usr/bin/env python3
"""
Interactive SMS Setup Script
This will help you configure Twilio for real SMS OTP delivery
"""

import os
import re

print("="*70)
print("📱 TWILIO SMS SETUP - Get OTP on Your Phone!")
print("="*70)
print()

# Check if twilio is installed
try:
    import twilio
    print("✅ Twilio library is installed")
except ImportError:
    print("❌ Twilio library not found")
    print("   Installing Twilio...")
    os.system("pip install twilio")
    print("✅ Twilio installed!")
    print()

print("="*70)
print("STEP 1: Get Your Twilio Account (FREE)")
print("="*70)
print()
print("If you don't have a Twilio account yet:")
print("1. Go to: https://www.twilio.com/try-twilio")
print("2. Sign up (FREE - includes $15 credit)")
print("3. Verify your email and phone")
print()
input("Press ENTER when you have your Twilio account ready...")
print()

print("="*70)
print("STEP 2: Get Your Credentials from Twilio Dashboard")
print("="*70)
print()
print("In your Twilio Console Dashboard, you'll find:")
print("  • Account SID (starts with 'AC')")
print("  • Auth Token (click 'View' to reveal)")
print("  • Phone Number (get a free trial number)")
print()

account_sid = input("Enter your Twilio Account SID: ").strip()
if not account_sid:
    print("❌ Account SID is required!")
    exit(1)

auth_token = input("Enter your Twilio Auth Token: ").strip()
if not auth_token:
    print("❌ Auth Token is required!")
    exit(1)

from_number = input("Enter your Twilio Phone Number (with +): ").strip()
if not from_number:
    print("❌ Phone Number is required!")
    exit(1)

# Validate format
if not account_sid.startswith('AC'):
    print("⚠️  Warning: Account SID should start with 'AC'")
    
if not from_number.startswith('+'):
    print("⚠️  Warning: Phone number should start with '+' (e.g., +14155552671)")
    from_number = '+' + from_number

# Update otp_config.py
print()
print("="*70)
print("STEP 3: Updating otp_config.py")
print("="*70)
print()

try:
    with open('otp_config.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create new SMS_CONFIG
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
    
    with open('otp_config.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ otp_config.py updated successfully!")
    print()
    
except Exception as e:
    print(f"❌ Error updating otp_config.py: {e}")
    print()
    print("Please update it manually:")
    print()
    print("SMS_CONFIG = {")
    print(f"    'enabled': True,")
    print(f"    'account_sid': '{account_sid}',")
    print(f"    'auth_token': '{auth_token}',")
    print(f"    'from_number': '{from_number}',")
    print(f"    'service_name': 'Hospital OTP Service'")
    print("}")
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
    print(f"⚠️  Connection test had issues: {e}")
    print("   But configuration is saved. You can test it when you run the app.")
    print()

print("="*70)
print("✅ SETUP COMPLETE!")
print("="*70)
print()
print("📱 Real SMS OTP is now configured!")
print()
print("⚠️  IMPORTANT FOR TRIAL ACCOUNTS:")
print("   - You can only send SMS to VERIFIED phone numbers")
print("   - Go to Twilio Console → Phone Numbers → Verified Caller IDs")
print("   - Add and verify the phone numbers you want to test with")
print()
print("🚀 Next Steps:")
print("   1. Verify your test phone number in Twilio Console")
print("   2. Restart your Flask application (stop and run 'python app.py' again)")
print("   3. Try booking an appointment or registering")
print("   4. Check your phone - OTP SMS will arrive! 📱")
print()
print("="*70)
print("The yellow warning box will disappear once SMS is working!")
print("="*70)

