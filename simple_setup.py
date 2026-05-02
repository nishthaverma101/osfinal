#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Twilio Setup for Hospital Management System
"""

def setup_twilio():
    print("Setting up Twilio for Real-Time SMS OTP")
    print("=" * 50)
    
    print("\nPlease enter your Twilio credentials:")
    print("(You can find these in your Twilio Console Dashboard)")
    print()
    
    account_sid = input("Enter your Twilio Account SID: ").strip()
    auth_token = input("Enter your Twilio Auth Token: ").strip()
    from_number = input("Enter your Twilio Phone Number (e.g., +1234567890): ").strip()
    
    if not all([account_sid, auth_token, from_number]):
        print("Error: All fields are required!")
        return False
    
    # Update otp_config.py
    config_content = f'''# OTP Configuration for Hospital Management System
# Update these settings for production use

# SMS Configuration (Twilio)
SMS_CONFIG = {{
    'enabled': True,  # Real SMS sending enabled
    'account_sid': '{account_sid}',
    'auth_token': '{auth_token}',
    'from_number': '{from_number}',
    'service_name': 'Hospital OTP Service'
}}

# Email Configuration (SMTP)
EMAIL_CONFIG = {{
    'enabled': False,  # Set to True to enable real email sending
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password',
    'sender_name': 'Hospital Management System'
}}

# OTP Settings
OTP_CONFIG = {{
    'length': 6,
    'expiry_minutes': 10,
    'max_attempts': 3,
    'cooldown_minutes': 5
}}

# IPC Configuration
IPC_CONFIG = {{
    'enabled': True,
    'method': 'console',  # Options: 'console', 'redis', 'rabbitmq', 'websocket'
    'redis_url': 'redis://localhost:6379/0',
    'rabbitmq_url': 'amqp://localhost:5672',
    'websocket_url': 'ws://localhost:8000/ws'
}}

# Production Settings
PRODUCTION_CONFIG = {{
    'debug_mode': True,  # Set to False in production
    'log_level': 'INFO',
    'rate_limiting': True,
    'max_requests_per_minute': 60
}}
'''
    
    try:
        with open('otp_config.py', 'w') as f:
            f.write(config_content)
        print("Configuration updated successfully!")
    except Exception as e:
        print(f"Error updating configuration: {e}")
        return False
    
    # Test Twilio connection
    print("\nTesting Twilio connection...")
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        
        # Get account info to verify credentials
        account = client.api.accounts(account_sid).fetch()
        print(f"Twilio connection successful!")
        print(f"Account Name: {account.friendly_name}")
        print(f"Account Status: {account.status}")
        
    except Exception as e:
        print(f"Twilio connection failed: {e}")
        print("Please check your credentials and try again.")
        return False
    
    print("\nSetup Complete!")
    print("=" * 50)
    print("Real-time SMS OTP is now enabled!")
    print("Your Twilio credentials are configured")
    print("SMS will be sent to mobile numbers")
    print()
    print("Next Steps:")
    print("1. Start the Flask app: python app.py")
    print("2. Go to: http://localhost:5000")
    print("3. Click 'Book Appointment'")
    print("4. Enter your mobile number")
    print("5. Check your phone for SMS with OTP!")
    print()
    print("Test with existing patient numbers:")
    print("- 6939585183 (David Williams)")
    print("- 8228188767 (Emily Smith)")
    
    return True

if __name__ == "__main__":
    print("Hospital Management System - Twilio Setup")
    print("This script will configure real-time SMS OTP sending")
    print()
    
    # Check if twilio is installed
    try:
        import twilio
        print("Twilio library is installed")
    except ImportError:
        print("Twilio library not found!")
        print("Please install it first: pip install twilio")
        exit(1)
    
    # Run setup
    if setup_twilio():
        print("\nReady to send real OTPs!")
    else:
        print("\nSetup failed. Please try again.")
        exit(1)



