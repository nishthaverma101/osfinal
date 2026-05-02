# 🚀 Quick Start Guide

## ⚡ Fastest Way to Run

### Windows:
1. Double-click `START_SERVER.bat`
2. Open browser to `http://localhost:5000`

### Mac/Linux:
1. Open Terminal in this folder
2. Run: `chmod +x START_SERVER.sh && ./START_SERVER.sh`
3. Open browser to `http://localhost:5000`

## 📦 First Time Setup

### Step 1: Install Python
- Download from: https://www.python.org/downloads/
- **Important**: Check "Add Python to PATH" during installation

### Step 2: Install Dependencies
Open Command Prompt/Terminal in the `oss` folder and run:
```bash
pip install -r requirements.txt
```

### Step 3: Run the Server
```bash
python app.py
```

### Step 4: Open Browser
Go to: **http://localhost:5000**

## 🔑 Login Credentials

### Admin:
- URL: http://localhost:5000/admin/login
- Email: `admin@gmail.com`
- Password: `admin`

### Doctor:
- URL: http://localhost:5000/doctor/login
- Doctor ID: `D001`, `D002`, `D003`, etc.
- Password: `{DoctorID}123` (e.g., `D001123`)

### Patient:
- URL: http://localhost:5000/patient/login
- Uses OTP verification

## ❓ Troubleshooting

**"Python not found"** → Install Python from python.org

**"pip not found"** → Use `python -m pip install -r requirements.txt`

**"Module not found"** → Run `pip install Flask pandas`

**Port 5000 in use** → Change port in `app.py` line 2102

## 📖 Full Documentation

See `SETUP_GUIDE.md` for detailed instructions.

