# 📱 Real SMS Setup Instructions

## To Enable Real SMS OTP System

The OTP system is currently in **debug mode** (showing OTP on screen). To enable real SMS sending:

### Step 1: Get Twilio Account (FREE Trial Available)

1. Go to [https://www.twilio.com](https://www.twilio.com)
2. Sign up for a FREE account (includes $15 credit)
3. Verify your phone number
4. Get your credentials from the Twilio Console:
   - **Account SID**: Found in Dashboard
   - **Auth Token**: Found in Dashboard (click to reveal)
   - **Phone Number**: Get a free trial number from Twilio

### Step 2: Update Configuration

Open `otp_config.py` and replace the placeholder values:

```python
SMS_CONFIG = {
    'enabled': True,  # Keep this as True
    'account_sid': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  # Your Account SID from Twilio
    'auth_token': 'your_actual_auth_token_here',      # Your Auth Token from Twilio
    'from_number': '+1234567890',                      # Your Twilio phone number (with + and country code)
    'service_name': 'Hospital OTP Service'
}
```

### Step 3: Install Twilio Library

```bash
pip install twilio
```

### Step 4: Test

1. Restart your Flask application
2. Try registering a patient or logging in
3. You should receive real SMS with OTP on your phone!

### Important Notes:

- **Free Trial**: Twilio free trial allows sending SMS to verified numbers only
- **Cost**: After trial, SMS costs ~$0.0075 per message
- **Country Code**: Make sure phone numbers include country code (e.g., +91 for India, +1 for US)
- **Verification**: You need to verify recipient numbers in Twilio console during trial period

### Alternative: Use Demo Mode

If you don't want to set up Twilio right now, the system will continue showing OTP on screen in debug mode. This is fine for development/testing.

