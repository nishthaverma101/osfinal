#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test SMS sending with Twilio
"""

def test_sms():
    print("Testing SMS Sending with Twilio")
    print("=" * 40)
    
    try:
        from otp_config import SMS_CONFIG
        from twilio.rest import Client
        
        if not SMS_CONFIG['enabled']:
            print("SMS is disabled in configuration")
            return False
        
        # Test phone number
        test_number = input("Enter your phone number to test (e.g., 9876543210): ").strip()
        if not test_number:
            print("Phone number is required")
            return False
        
        # Add country code if not present
        if not test_number.startswith('+'):
            test_number = f'+91{test_number}' if len(test_number) == 10 else f'+{test_number}'
        
        print(f"\nSending test SMS to: {test_number}")
        
        # Create Twilio client
        client = Client(SMS_CONFIG['account_sid'], SMS_CONFIG['auth_token'])
        
        # Send test message
        message = client.messages.create(
            body='Hospital Management System\n\nTest SMS successful!\n\nYour Twilio setup is working correctly.',
            from_=SMS_CONFIG['from_number'],
            to=test_number
        )
        
        print("SMS sent successfully!")
        print(f"Message SID: {message.sid}")
        print(f"Status: {message.status}")
        print(f"To: {message.to}")
        print(f"From: {message.from_}")
        
        print("\nTwilio setup is working!")
        print("You should receive the test SMS on your phone shortly.")
        
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please install Twilio: pip install twilio")
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Twilio credentials in otp_config.py")
        print("2. Verify your phone number format (+countrycode)")
        print("3. Check your Twilio account balance")
        print("4. Ensure your Twilio number is verified")
        return False

if __name__ == "__main__":
    print("Hospital Management System - SMS Test")
    print("This will send a test SMS to verify your Twilio setup")
    print()
    
    if test_sms():
        print("\nTest completed successfully!")
        print("You can now use the appointment booking system with real SMS OTP.")
    else:
        print("\nTest failed. Please check your configuration.")



