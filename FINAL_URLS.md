# 🎯 Final Project URLs - CareQueue Hospital Management System

## 🚀 MAIN PROJECT URL

### Homepage (Start Here):
```
http://localhost:5000
```

---

## 🔐 ADMIN DASHBOARD (Simplified Access)

### Direct Access (No Login Required):
```
http://localhost:5000/admin
```

**OR**

```
http://localhost:5000/admin/dashboard
```

**OR**

```
http://localhost:5000/admin/login
```

**All three URLs now work directly - no login needed!**

---

## 📋 Complete URL List

### 🏠 Main Pages
- **Homepage**: `http://localhost:5000`
- **Index**: `http://localhost:5000/index`

### 👨‍⚕️ Admin Dashboard
- **Admin Dashboard**: `http://localhost:5000/admin` ⭐ **USE THIS**
- **Admin Dashboard (Alt)**: `http://localhost:5000/admin/dashboard`
- **Admin Login**: `http://localhost:5000/admin/login` (auto-redirects)
- **Admin Logout**: `http://localhost:5000/admin/logout`

### 👨‍⚕️ Doctor Dashboard
- **Doctor Login**: `http://localhost:5000/doctor/login`
- **Doctor Dashboard**: `http://localhost:5000/doctor/<doctor_id>` (e.g., `/doctor/D001`)

### 👤 Patient Services
- **Patient Login**: `http://localhost:5000/patient/login`
- **Patient Registration**: `http://localhost:5000/register`
- **Book Appointment**: `http://localhost:5000/book`
- **Patient Dashboard**: `http://localhost:5000/patient/<patient_id>`

### 🧪 Lab Reports
- **Upload Lab Report**: `http://localhost:5000/lab/upload`
- **View Lab Reports**: `http://localhost:5000/lab/reports`
- **View Specific Report**: `http://localhost:5000/report/<report_id>/view`

---

## 🎯 Quick Access Guide

### Step 1: Start Server
```bash
cd oss
python app.py
```

### Step 2: Open Homepage
```
http://localhost:5000
```

### Step 3: Access Admin Dashboard
```
http://localhost:5000/admin
```

**That's it! No login required for admin dashboard.**

---

## ✅ What's Changed

1. ✅ **"Find Patient" removed** - No longer in patient services section
2. ✅ **Admin login simplified** - Direct access, no credentials needed
3. ✅ **All admin URLs work** - `/admin`, `/admin/dashboard`, `/admin/login` all redirect to dashboard

---

## 🔑 Login Credentials (For Reference)

### Admin:
- **URL**: `http://localhost:5000/admin` (No login needed!)
- ~~Email: `admin@gmail.com`~~ (Not needed anymore)
- ~~Password: `admin`~~ (Not needed anymore)

### Doctor:
- **URL**: `http://localhost:5000/doctor/login`
- **Doctor ID**: `D001`, `D002`, `D003`, etc.
- **Password**: `{DoctorID}123` (e.g., `D001123`)

### Patient:
- **URL**: `http://localhost:5000/patient/login`
- **Method**: OTP via SMS/Email

---

## 📱 Network Access

To access from other devices on the same network:

1. Find your IP address (Windows: `ipconfig`, Mac/Linux: `ifconfig`)
2. Use: `http://YOUR_IP_ADDRESS:5000`
3. Admin: `http://YOUR_IP_ADDRESS:5000/admin`

---

## 🎓 For Demonstration

### Recommended Flow:

1. **Start Server:**
   ```bash
   python app.py
   ```

2. **Open Homepage:**
   ```
   http://localhost:5000
   ```

3. **Access Admin Dashboard:**
   ```
   http://localhost:5000/admin
   ```
   **No login required!**

4. **Test Other Features:**
   - Doctor Login: `http://localhost:5000/doctor/login`
   - Patient Register: `http://localhost:5000/register`
   - Book Appointment: `http://localhost:5000/book`

---

## ⚠️ Important Notes

- ✅ Server must be running: `python app.py`
- ✅ Use `http://` not `https://`
- ✅ Port 5000 must be available
- ✅ Admin dashboard now has direct access (no login)

---

## 🎯 FINAL ANSWER

### Main Project URL:
```
http://localhost:5000
```

### Admin Dashboard URL:
```
http://localhost:5000/admin
```

**Both URLs work immediately - no login required for admin!**

---

**Last Updated**: After final simplifications
**Status**: ✅ Ready for use

