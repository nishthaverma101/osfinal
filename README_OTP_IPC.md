# OTP & IPC System Setup Guide

## 🚀 **Real OTP Sending Setup**

### **For SMS (Twilio) - RECOMMENDED**

1. **Sign up for Twilio**:
   - Go to [twilio.com](https://www.twilio.com)
   - Create a free account (includes $15 credit)
   - Get your Account SID and Auth Token

2. **Update Configuration**:
   ```python
   # In otp_config.py
   SMS_CONFIG = {
       'enabled': True,  # Enable real SMS
       'account_sid': 'your_actual_account_sid',
       'auth_token': 'your_actual_auth_token',
       'from_number': '+1234567890',  # Your Twilio number
   }
   ```

3. **Install Twilio**:
   ```bash
   pip install twilio
   ```

### **For Email (Gmail) - ALTERNATIVE**

1. **Enable App Passwords**:
   - Go to Google Account settings
   - Enable 2-Factor Authentication
   - Generate an App Password for this application

2. **Update Configuration**:
   ```python
   # In otp_config.py
   EMAIL_CONFIG = {
       'enabled': True,  # Enable real email
       'sender_email': 'your-email@gmail.com',
       'sender_password': 'your-16-char-app-password',
   }
   ```

## 🔧 **IPC System Features**

### **Current Implementation**
- **Console Logging**: Shows IPC messages in terminal
- **Real-time Notifications**: Simulates doctor notifications
- **Data Validation**: Ensures all required fields are present

### **Production IPC Options**

#### **Option 1: Redis (Recommended)**
```bash
pip install redis
```
```python
# In otp_config.py
IPC_CONFIG = {
    'method': 'redis',
    'redis_url': 'redis://localhost:6379/0'
}
```

#### **Option 2: RabbitMQ**
```bash
pip install pika
```
```python
# In otp_config.py
IPC_CONFIG = {
    'method': 'rabbitmq',
    'rabbitmq_url': 'amqp://localhost:5672'
}
```

#### **Option 3: WebSocket (Real-time)**
```bash
pip install websockets
```
```python
# In otp_config.py
IPC_CONFIG = {
    'method': 'websocket',
    'websocket_url': 'ws://localhost:8000/ws'
}
```

## 📱 **How to Test OTP System**

### **Step 1: Enable Demo Mode**
```python
# In otp_config.py - Keep these as False for testing
SMS_CONFIG = {'enabled': False}
EMAIL_CONFIG = {'enabled': False}
```

### **Step 2: Test the Flow**
1. Go to `http://localhost:5000`
2. Click "Book Appointment"
3. Enter mobile: `6939585183` and email: `david.williams@mail.com`
4. Check console for OTP (e.g., `123456`)
5. Enter OTP and complete booking

### **Step 3: Enable Real OTP**
1. Set up Twilio account
2. Update `otp_config.py` with real credentials
3. Set `SMS_CONFIG['enabled'] = True`
4. Test with your real phone number

## 🏥 **IPC System Testing**

### **Upload Lab Report**
1. Go to `http://localhost:5000`
2. Click "Upload Lab Report"
3. Select patient and doctor
4. Enter test details
5. Submit - check console for IPC messages

### **View Doctor Notifications**
1. Go to `http://localhost:5000/doctor/D001/lab_notifications`
2. See real-time lab notifications
3. Test "Mark as Reviewed" functionality

## 🔒 **Security Features**

### **OTP Security**
- ✅ 6-digit random OTP
- ✅ 10-minute expiry
- ✅ 3 max attempts
- ✅ 5-minute cooldown
- ✅ Secure session management

### **IPC Security**
- ✅ Data validation
- ✅ Error handling
- ✅ Audit logging
- ✅ Secure message format

## 🚨 **Troubleshooting**

### **SMS Not Working**
- Check Twilio credentials
- Verify phone number format (+countrycode)
- Check Twilio account balance
- Review console for error messages

### **Email Not Working**
- Verify Gmail app password
- Check 2FA is enabled
- Try different SMTP server
- Check firewall settings

### **IPC Not Working**
- Check Redis/RabbitMQ is running
- Verify connection URLs
- Check console for error messages
- Test with console method first

## 📊 **Production Deployment**

### **Environment Variables**
```bash
export TWILIO_ACCOUNT_SID="your_sid"
export TWILIO_AUTH_TOKEN="your_token"
export GMAIL_APP_PASSWORD="your_password"
export REDIS_URL="redis://localhost:6379/0"
```

### **Docker Support**
```dockerfile
# Add to Dockerfile
RUN pip install twilio redis pika
COPY otp_config.py .
```

### **Monitoring**
- Set up logging for OTP attempts
- Monitor IPC message queues
- Track delivery success rates
- Set up alerts for failures

## 🎯 **Next Steps**

1. **Enable Real OTP**: Set up Twilio for SMS
2. **Configure IPC**: Choose Redis/RabbitMQ for production
3. **Add Monitoring**: Set up logging and alerts
4. **Test Thoroughly**: Test with real phone numbers
5. **Deploy**: Use environment variables for production

---

**Need Help?** Check the console output for detailed error messages and debug information!




