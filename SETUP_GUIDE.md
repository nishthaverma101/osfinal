# CareQueue Hospital Management System - Setup Guide

## 🚀 Quick Start

This is a **Flask-based web application** that requires Python and some dependencies to run. You **cannot run it directly in a browser** without installing the required software first.

## 📋 Prerequisites

You need to install the following:

### 1. Python 3.8 or Higher
- **Download**: https://www.python.org/downloads/
- **Check if installed**: Open Command Prompt/Terminal and type:
  ```bash
  python --version
  ```
  or
  ```bash
  python3 --version
  ```

### 2. Install Python Dependencies

Once Python is installed, open Command Prompt/Terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

This will install:
- **Flask** (web framework)
- **pandas** (data manipulation)
- **twilio** (optional, for SMS - only needed if you want real SMS functionality)

## 🏃 How to Run the Project

### Step 1: Navigate to Project Folder
```bash
cd oss
```

### Step 2: Start the Flask Server
```bash
python app.py
```

or if `python` doesn't work:
```bash
python3 app.py
```

### Step 3: Open in Browser
Once you see:
```
 * Running on http://127.0.0.1:5000
```

Open your web browser and go to:
```
http://localhost:5000
```
or
```
http://127.0.0.1:5000
```

## 🌐 Accessing from Other Devices

### On the Same Network:
1. Find your computer's IP address:
   - **Windows**: Open Command Prompt, type `ipconfig`, look for "IPv4 Address"
   - **Mac/Linux**: Open Terminal, type `ifconfig` or `ip addr`

2. Modify `app.py` line 2063:
   ```python
   app.run(debug=True, host='0.0.0.0', port=5000)
   ```

3. Access from other devices using:
   ```
   http://YOUR_IP_ADDRESS:5000
   ```
   Example: `http://192.168.1.100:5000`

## 📁 Project Structure

```
oss/
├── app.py                 # Main Flask application
├── Hospital_utils.py      # Queue management utilities
├── ipc_bus.py            # Inter-process communication
├── lock_utils.py         # File locking for thread safety
├── otp_config.py         # OTP/SMS configuration
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
├── static/              # CSS, JS, uploaded files
├── *.csv                # Data files (patients, appointments, etc.)
└── README files         # Documentation
```

## 🔧 Troubleshooting

### Issue: "Python not found"
**Solution**: Install Python from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation

### Issue: "pip not found"
**Solution**: 
- On Windows: `python -m pip install -r requirements.txt`
- On Mac/Linux: `python3 -m pip install -r requirements.txt`

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution**: Install dependencies:
```bash
pip install Flask pandas
```

### Issue: "Port 5000 already in use"
**Solution**: Change the port in `app.py`:
```python
app.run(debug=True, port=5001)  # Use different port
```

### Issue: "Permission denied" on Windows
**Solution**: Run Command Prompt as Administrator

### Issue: CSV files showing errors
**Solution**: Make sure all CSV files are in the `oss/` folder and have proper permissions

## 🎯 Default Login Credentials

### Admin Dashboard:
- **Email**: `admin@gmail.com`
- **Password**: `admin`
- **URL**: `http://localhost:5000/admin/login`

### Doctor Login:
- **Doctor ID**: `D001`, `D002`, `D003`, etc.
- **Default Password**: `{DoctorID}123` (e.g., `D001123`)
- **URL**: `http://localhost:5000/doctor/login`

### Patient Login:
- Uses OTP verification via SMS/Email
- **URL**: `http://localhost:5000/patient/login`

## 📱 SMS/OTP Setup (Optional)

The system works without SMS, but if you want real SMS functionality:

1. Sign up at https://www.twilio.com (free trial with $15 credit)
2. Get your Account SID, Auth Token, and Phone Number
3. Update `otp_config.py` with your credentials
4. See `TWILIO_QUICK_SETUP.md` for detailed instructions

**Note**: Without Twilio, OTPs will be shown in console/logs for testing.

## 🔒 Security Notes

- This is a **development/demonstration** system
- **Do NOT use in production** without proper security hardening
- Default passwords should be changed in production
- CSV files are not encrypted - use a proper database for production

## 🆘 Getting Help

1. Check the console/terminal for error messages
2. Ensure all CSV files exist in the `oss/` folder
3. Verify Python and dependencies are installed correctly
4. Check that port 5000 is not blocked by firewall

## ✅ Quick Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] All CSV files present in `oss/` folder
- [ ] Flask server running (`python app.py`)
- [ ] Browser opened to `http://localhost:5000`
- [ ] Can see the homepage

## 🎓 For Demonstration

1. **Start the server**: `python app.py`
2. **Open browser**: `http://localhost:5000`
3. **Test admin login**: `admin@gmail.com` / `admin`
4. **Test doctor login**: `D001` / `D001123`
5. **Add appointments**: Use the "Add Patient" button on homepage
6. **View queues**: Check doctor dashboard to see priority/FCFS queues
7. **Test mutex**: See `MUTEX_DEMONSTRATION_GUIDE.md`

---

**Remember**: This is a local development server. It only runs while `python app.py` is active. Close the terminal/stop the process to stop the server.

