# 🚀 QUICK FIX - Make SMS Work in 3 Steps!

## The Problem
You're seeing the yellow warning box because Twilio credentials are not configured yet.

## The Solution (3 Simple Steps)

### ✅ Step 1: Twilio is Already Installed!
Good news - Twilio library is already installed on your system.

### 📝 Step 2: Get Your Twilio Credentials

**If you don't have a Twilio account:**
1. Go to: **https://www.twilio.com/try-twilio**
2. Sign up (FREE - includes $15 credit)
3. Verify your email and phone

**Get your credentials from Twilio Dashboard:**
- **Account SID**: Found on main dashboard (starts with `AC`)
- **Auth Token**: Click "View" to reveal (keep secret!)
- **Phone Number**: Get a free trial number from "Phone Numbers"

### ⚙️ Step 3: Run the Setup Script

**Option A: Use the interactive script (EASIEST)**
```bash
python setup_sms.py
```

This will:
- Ask you for your Twilio credentials
- Update `otp_config.py` automatically
- Test the connection

**Option B: Manual setup**

Open `otp_config.py` and replace:

```python
SMS_CONFIG = {
    'enabled': True,
    'account_sid': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  # ← Your Account SID
    'auth_token': 'your_actual_auth_token_here',         # ← Your Auth Token
    'from_number': '+14155552671',                         # ← Your Twilio number
    'service_name': 'Hospital OTP Service'
}
```

### 🔐 Step 4: Verify Phone Numbers (Trial Accounts)

**IMPORTANT**: Free trial can only send to verified numbers!

1. Twilio Console → **Phone Numbers** → **Verified Caller IDs**
2. Click **"Add a new Caller ID"**
3. Enter your phone number
4. Verify via call or SMS

### 🚀 Step 5: Test It!

1. **Restart your app**: Stop it (Ctrl+C) and run `python app.py` again
2. **Try booking/registering** with your verified phone number
3. **Check your phone** - OTP SMS will arrive! 📱

---

## That's It! 🎉

Once configured, the yellow warning box will disappear and OTP will be sent to your phone!

---

## Need Help?

- Run: `python setup_sms.py` for interactive setup
- See `START_HERE_SMS.md` for detailed guide
- Check console output for error messages

