# 📱 GET OTP ON YOUR PHONE - START HERE!

## The Problem
Right now, OTP is showing on screen because **Twilio SMS is not configured yet**.

## The Solution (5 Minutes)

### Step 1: Install Twilio
Open Command Prompt or PowerShell and run:
```bash
pip install twilio
```

If that doesn't work, try:
```bash
python -m pip install twilio
```

### Step 2: Get FREE Twilio Account
1. **Go to**: https://www.twilio.com/try-twilio
2. **Click**: "Sign up" (it's FREE - includes $15 credit)
3. **Enter**: Your email and create password
4. **Verify**: Your email and phone number

### Step 3: Get Your Credentials
After signing up, in your Twilio Dashboard:

1. **Account SID**: 
   - On main dashboard, copy the "Account SID"
   - Looks like: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

2. **Auth Token**: 
   - On main dashboard, find "Auth Token"
   - Click "View" to reveal it
   - Copy it (keep it secret!)

3. **Phone Number**:
   - Click "Phone Numbers" in left menu
   - Click "Buy a number" or "Get a number"
   - Choose a number (FREE during trial)
   - Copy it (e.g., `+14155552671`)

### Step 4: Update `otp_config.py`

Open `otp_config.py` file and replace these lines:

```python
SMS_CONFIG = {
    'enabled': True,
    'account_sid': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',  # ← Paste your Account SID
    'auth_token': 'your_actual_auth_token_here',         # ← Paste your Auth Token
    'from_number': '+14155552671',                         # ← Paste your Twilio number
    'service_name': 'Hospital OTP Service'
}
```

**Example with real values:**
```python
SMS_CONFIG = {
    'enabled': True,
    'account_sid': 'ACa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6',
    'auth_token': 'abc123def456ghi789jkl012mno345pqr',
    'from_number': '+14155552671',
    'service_name': 'Hospital OTP Service'
}
```

### Step 5: Verify Your Phone Number (IMPORTANT!)

**For FREE trial accounts**, you can only send SMS to **verified numbers**:

1. In Twilio Console, go to: **Phone Numbers** → **Verified Caller IDs**
2. Click **"Add a new Caller ID"**
3. Enter **your phone number** (the one you'll test with)
4. Choose verification method (call or SMS)
5. Enter the code you receive
6. ✅ Number is now verified!

### Step 6: Restart Your App

1. **Stop** your Flask app (Ctrl+C)
2. **Start** it again: `python app.py`
3. **Try** booking an appointment or registering
4. **Check your phone** - OTP SMS will arrive! 📱

---

## What You'll Receive

Once configured, you'll get an SMS like:
```
🏥 CareQueue Hospital

Your OTP is: 123456

Valid for 10 minutes.

Do not share this code with anyone.
```

---

## Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'twilio'"
**Fix**: Run `pip install twilio` again

### ❌ "SMS not received"
**Check**:
- Phone number is verified in Twilio Console (for trial accounts)
- Phone number format is correct (with country code: +91 for India)
- Credentials in `otp_config.py` are correct
- Check Twilio Console → Logs → Messaging for errors

### ❌ "Invalid phone number"
**Fix**: Use country code:
- India: `+91XXXXXXXXXX` (10 digits after +91)
- USA: `+1XXXXXXXXXX` (10 digits after +1)

### ❌ "Trial account restrictions"
**Fix**: 
- Verify recipient number in Twilio Console
- Or upgrade to paid account ($20/month minimum)

---

## Need More Help?

- See `TWILIO_QUICK_SETUP.md` for detailed guide
- Check console output when you run the app
- Twilio Support: https://support.twilio.com

---

## Cost

- **Free Trial**: $15 credit (enough for ~2000 SMS)
- **After Trial**: ~$0.0075 per SMS (less than 1 cent!)
- **Monthly**: Pay only for what you use

---

**Once you complete these steps, OTP will be sent to your phone just like banks!** 🎉

