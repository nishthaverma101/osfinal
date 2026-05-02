# OTP Configuration for Hospital Management System
# Update these settings for production use

# SMS Configuration (Twilio)
SMS_CONFIG = {
    'enabled': True,  # Set to True to enable real SMS sending
    'account_sid': 'your_twilio_account_sid',
    'auth_token': 'your_twilio_auth_token',
    'from_number': '+1234567890',  # Your Twilio phone number
    'service_name': 'Hospital OTP Service'
}

# Email Configuration (SMTP)
EMAIL_CONFIG = {
    'enabled': False,  # Set to True to enable real email sending
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password',  # Use app password for Gmail
    'sender_name': 'Hospital Management System'
}

# OTP Settings
OTP_CONFIG = {
    'length': 6,
    'expiry_minutes': 10,
    'max_attempts': 3,
    'cooldown_minutes': 5
}

# IPC Configuration
IPC_CONFIG = {
    'enabled': True,
    'method': 'console',  # Options: 'console', 'redis', 'rabbitmq', 'websocket'
    'redis_url': 'redis://localhost:6379/0',
    'rabbitmq_url': 'amqp://localhost:5672',
    'websocket_url': 'ws://localhost:8000/ws'
}

# Production Settings
PRODUCTION_CONFIG = {
    'debug_mode': True,  # Set to False in production
    'log_level': 'INFO',
    'rate_limiting': True,
    'max_requests_per_minute': 60
}

