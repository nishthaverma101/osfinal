# 🚀 Enable Real SMS OTP RIGHT NOW!

## Quick Setup (5 Minutes)

### Step 1: Install Twilio Library
```bash
pip install twilio
```

### Step 2: Get FREE Twilio Account
1. Go to: **https://www.twilio.com/try-twilio**
2. Sign up (FREE - includes $15 credit)
3. Verify your email and phone

### Step 3: Get Your Credentials
After signing up, in Twilio Dashboard:

1. **Account SID**: Copy from main dashboard (starts with `AC`)
2. **Auth Token**: Click "View" to reveal (keep this secret!)
3. **Phone Number**: 
   - Go to "Phone Numbers" → "Buy a number"
   - Get a FREE trial number
   - Copy it (e.g., `+14155552671`)

### Step 4: Update `otp_config.py`

Open `otp_config.py` and replace:

```python
SMS_CONFIG = {
    'enabled': True,
    'account_sid': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  # ← Your Account SID
    'auth_token': 'your_actual_auth_token_here',         # ← Your Auth Token
    'from_number': '+1234567890',                         # ← Your Twilio number
    'service_name': 'Hospital OTP Service'
}
```

### Step 5: Verify Your Phone Number (Trial Accounts)

**IMPORTANT**: Free trial can only send to verified numbers!

1. Twilio Console → "Phone Numbers" → "Verified Caller IDs"
2. Click "Add a new Caller ID"
3. Enter your phone number
4. Verify via call or SMS

### Step 6: Test It!

1. Restart your app: `python app.py`
2. Try registering/login with your verified number
3. **Check your phone** - OTP SMS will arrive! 📱

---

## That's It! 🎉

Your OTP will now be sent via **real SMS** just like banks!

---

## Need Help?

- See `TWILIO_QUICK_SETUP.md` for detailed guide
- Check console output for error messages
- Twilio Support: https://support.twilio.com

