# 🌐 CareQueue Hospital Management System - Complete URL Guide

## 🚀 Quick Start

**First, start the server:**
```bash
python app.py
```

**Then open your browser to:**
```
http://localhost:5000
```

---

## 📋 Complete URL List

### 🏠 Main Pages

| URL | Description | Access |
|-----|-------------|--------|
| `http://localhost:5000/` | **Homepage** - Main landing page with project overview | Public |
| `http://localhost:5000/index` | Alternative homepage URL | Public |

---

### 👨‍⚕️ Admin Dashboard (Multiple Access Methods)

| URL | Description | Method |
|-----|-------------|--------|
| `http://localhost:5000/admin/login?auto=login` | **Auto-login** (Easiest - No credentials needed!) | GET |
| `http://localhost:5000/admin?admin_key=carequeue2024` | **Secure Key Access** (Direct access) | GET |
| `http://localhost:5000/admin?direct=true` | **Direct Bypass** (Testing only) | GET |
| `http://localhost:5000/admin/login` | **Standard Login Page** | GET/POST |
| `http://localhost:5000/admin` | **Admin Dashboard** (Requires login) | GET |
| `http://localhost:5000/admin/dashboard` | Alternative admin dashboard URL | GET |
| `http://localhost:5000/admin/logout` | **Admin Logout** | GET |

**Admin Credentials (for standard login):**
- Email: `admin@gmail.com`
- Password: `admin`

---

### 👨‍⚕️ Doctor Dashboard

| URL | Description | Access |
|-----|-------------|--------|
| `http://localhost:5000/doctor/login` | **Doctor Login Page** | Public |
| `http://localhost:5000/doctor/<doctor_id>` | **Doctor Dashboard** (e.g., `/doctor/D001`) | Requires Login |
| `http://localhost:5000/doctor/<doctor_id>/lab_notifications` | **Lab Notifications** for doctor | Requires Login |

**Doctor Login:**
- Doctor ID: `D001`, `D002`, `D003`, etc.
- Default Password: `{DoctorID}123` (e.g., `D001123`)

---

### 👤 Patient Dashboard

| URL | Description | Access |
|-----|-------------|--------|
| `http://localhost:5000/patient/login` | **Patient Login Page** (OTP-based) | Public |
| `http://localhost:5000/patient/<patient_id>` | **Patient Dashboard** (e.g., `/patient/P001`) | Requires OTP Login |
| `http://localhost:5000/register` | **Patient Registration** | Public |
| `http://localhost:5000/book` | **Book Appointment** | Public |
| `http://localhost:5000/lookup` | **Patient Lookup** (Removed from homepage but URL still works) | Public |

---

### 📋 Appointments & Patients

| URL | Description | Method |
|-----|-------------|--------|
| `http://localhost:5000/add_patient` | **Add/Update Patient** (From homepage modal) | POST |
| `http://localhost:5000/start_consultation` | **Start Consultation** | POST |
| `http://localhost:5000/complete_consultation` | **Complete Consultation** | POST |
| `http://localhost:5000/call_next` | **Call Next Patient** (Doctor dashboard) | POST |

---

### 🧪 Lab Reports

| URL | Description | Access |
|-----|-------------|--------|
| `http://localhost:5000/lab/upload` | **Upload Lab Report** | Public/Admin |
| `http://localhost:5000/lab/reports` | **View All Lab Reports** | Public/Admin |
| `http://localhost:5000/report/<report_id>/view` | **View Specific Report** (e.g., `/report/R1007/view`) | Public |

---

### 💰 Billing

| URL | Description | Method |
|-----|-------------|--------|
| `http://localhost:5000/admin/update_payment_status` | **Update Payment Status** (Admin only) | POST |
| `http://localhost:5000/admin/call_next` | **Call Next Patient** (Admin dashboard) | POST |

---

### 🔍 Other Pages

| URL | Description | Access |
|-----|-------------|--------|
| `http://localhost:5000/view_report/<report_id>` | View lab report details | Public |

---

## 🎯 Most Important URLs (Quick Reference)

### For Testing/Demo:

1. **Homepage:**
   ```
   http://localhost:5000
   ```

2. **Admin Dashboard (Easiest Access):**
   ```
   http://localhost:5000/admin/login?auto=login
   ```
   OR
   ```
   http://localhost:5000/admin?admin_key=carequeue2024
   ```

3. **Doctor Login:**
   ```
   http://localhost:5000/doctor/login
   ```
   - Doctor ID: `D001`
   - Password: `D001123`

4. **Patient Registration:**
   ```
   http://localhost:5000/register
   ```

5. **Book Appointment:**
   ```
   http://localhost:5000/book
   ```

6. **Upload Lab Report:**
   ```
   http://localhost:5000/lab/upload
   ```

---

## 🌍 Network Access (From Other Devices)

If you want to access from other devices on the same network:

1. **Find your computer's IP address:**
   - Windows: Open Command Prompt, type `ipconfig`, look for "IPv4 Address"
   - Mac/Linux: Open Terminal, type `ifconfig` or `ip addr`

2. **Access using your IP:**
   ```
   http://YOUR_IP_ADDRESS:5000
   ```
   Example: `http://192.168.1.100:5000`

3. **Admin dashboard from network:**
   ```
   http://YOUR_IP_ADDRESS:5000/admin/login?auto=login
   ```

---

## 📱 Mobile Access

The project is responsive and works on mobile devices. Use the same URLs from your mobile browser when connected to the same network.

---

## 🔐 Authentication Summary

### Admin:
- **Auto-login URL**: `http://localhost:5000/admin/login?auto=login`
- **Standard Login**: `admin@gmail.com` / `admin`

### Doctor:
- **Login URL**: `http://localhost:5000/doctor/login`
- **Credentials**: `D001` / `D001123` (or any doctor ID)

### Patient:
- **Login URL**: `http://localhost:5000/patient/login`
- **Method**: OTP via SMS/Email

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
   http://localhost:5000/admin/login?auto=login
   ```

4. **Test Doctor Login:**
   ```
   http://localhost:5000/doctor/login
   ```
   - Login as `D001` / `D001123`

5. **Test Patient Registration:**
   ```
   http://localhost:5000/register
   ```

6. **Test Appointment Booking:**
   ```
   http://localhost:5000/book
   ```

---

## ⚠️ Important Notes

1. **Server Must Be Running**: All URLs only work when `python app.py` is running
2. **Localhost Only**: By default, only accessible from the same computer
3. **Port 5000**: Make sure port 5000 is not blocked by firewall
4. **HTTP Not HTTPS**: Use `http://` not `https://` for localhost

---

## 🐛 Troubleshooting

### "Connection Refused" or "Can't Reach Page"
- ✅ Check server is running: `python app.py`
- ✅ Check URL is correct: `http://localhost:5000` (not `https://`)
- ✅ Check port 5000 is not in use

### "404 Not Found"
- ✅ Check the URL spelling
- ✅ Make sure server is running
- ✅ Check server console for errors

### Admin Login Not Working
- ✅ Use auto-login URL: `http://localhost:5000/admin/login?auto=login`
- ✅ Or use secure key: `http://localhost:5000/admin?admin_key=carequeue2024`

---

## 📝 URL Parameters

### Admin Auto-Login:
```
?auto=login
```

### Admin Secure Key:
```
?admin_key=carequeue2024
```

### Admin Direct Bypass:
```
?direct=true
```

### Redirect After Login:
```
?next=/admin
```

---

## 🎯 Bookmark These URLs

For quick access, bookmark these in your browser:

1. **Homepage**: `http://localhost:5000`
2. **Admin (Auto)**: `http://localhost:5000/admin/login?auto=login`
3. **Doctor Login**: `http://localhost:5000/doctor/login`
4. **Patient Register**: `http://localhost:5000/register`

---

**Last Updated**: After all recent changes
**Server Port**: 5000
**Default Host**: localhost (0.0.0.0 for network access)

