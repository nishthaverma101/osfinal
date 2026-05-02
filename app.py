from flask import flash, Flask, render_template, request, redirect, url_for, jsonify, session
import pandas as pd
from contextlib import contextmanager
import threading
from datetime import datetime
from Hospital_utils import (
    clean_and_prepare_data,
    apply_severity,
    update_patient_severity,
    start_consultation,
    complete_consultation,
)
from ipc_bus import publish_ipc_event, notification_ipc
from lock_utils import file_lock


app = Flask(__name__)
app.secret_key = "my_secret_key_123"  # Add this line
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
notification_ipc.start()

# --- Admin auth config ---
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin"


def is_admin_authenticated():
    """Check if admin is authenticated - multiple methods for reliability."""
    # Method 1: Check session flags
    logged_in_flag = session.get('admin_logged_in') is True
    is_admin_flag = session.get('is_admin') is True
    email_match = session.get('admin_email') == ADMIN_EMAIL
    
    # Method 2: Check query parameter (for direct access)
    direct_access = request.args.get('admin_key') == 'carequeue2024'
    
    # Any method works
    result = (logged_in_flag and email_match) or is_admin_flag or direct_access
    
    if not result:
        print(f"[AUTH CHECK] Failed - logged_in={logged_in_flag}, is_admin={is_admin_flag}, email_match={email_match}, direct_access={direct_access}")
    else:
        print(f"[AUTH CHECK] ✅ Authenticated")
    
    return result


def require_admin():
    """Check admin authentication - with fallback for testing."""
    # Allow direct access via query parameter for testing (remove in production)
    if request.args.get('admin_key') == 'bypass123':
        session['admin_logged_in'] = True
        session['admin_email'] = ADMIN_EMAIL
        return None
    
    if not is_admin_authenticated():
        flash('Please login as administrator to continue.', 'warning')
        return redirect(url_for('admin_login', next=request.path))
    return None


def _highlight_log(channel, message):
    bar = "=" * 12
    print(f"\n{bar} [{channel}] {message}\n{bar}")


class ScopedLockRegistry:
    """Provide fine-grained locks keyed by appointment ID."""

    def __init__(self):
        self._locks = {}
        self._registry_lock = threading.RLock()

    def _get_lock(self, key: str) -> threading.RLock:
        normalized = str(key)
        with self._registry_lock:
            if normalized not in self._locks:
                self._locks[normalized] = threading.RLock()
            return self._locks[normalized]

    @contextmanager
    def guard(self, key: str):
        if key is None:
            raise ValueError("Lock key cannot be None")
        lock = self._get_lock(key)
        with lock:
            yield


appointment_lock_registry = ScopedLockRegistry()
global_appointments_lock = threading.RLock()
_mutex_state_lock = threading.RLock()
_active_mutexes = {}


@contextmanager
def _global_lock_ctx():
    global_appointments_lock.acquire()
    try:
        yield
    finally:
        global_appointments_lock.release()


def _record_mutex_acquire(key, context):
    with _mutex_state_lock:
        _active_mutexes[key] = {
            'context': context or 'unknown',
            'since': datetime.utcnow().strftime('%H:%M:%S')
        }


def _record_mutex_release(key):
    with _mutex_state_lock:
        _active_mutexes.pop(key, None)


def get_mutex_snapshot():
    with _mutex_state_lock:
        return dict(_active_mutexes)


@contextmanager
def appointment_guard(appointment_id=None, context_label=""):
    """
    Guard modifications to appointments.
    - If appointment_id is provided, use a scoped lock so different patients can update in parallel.
    - Otherwise fall back to a global lock (used when creating brand new appointments).
    """
    key = str(appointment_id) if appointment_id else "GLOBAL"
    try:
        default_context = request.path
    except RuntimeError:
        default_context = 'background-task'
    context = context_label or default_context
    
    _highlight_log("MUTEX 🔒", f"Waiting for lock [{key}] (context: {context})")
    
    # Use scoped lock for specific appointment, global lock for new appointments
    if appointment_id:
        ctx = appointment_lock_registry.guard(str(appointment_id))
    else:
        ctx = _global_lock_ctx()
    
    with ctx:
        _record_mutex_acquire(key, context)
        _highlight_log("MUTEX ✅", f"Lock acquired [{key}] (context: {context})")
        try:
            yield
        finally:
            _record_mutex_release(key)
            _highlight_log("MUTEX 🔓", f"Lock released [{key}] (context: {context})")


import os

# Resolve CSV paths relative to this file's directory so the app runs anywhere
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
appointments_path = os.path.join(BASE_DIR, 'appointments.csv')
treatments_path = os.path.join(BASE_DIR, 'treatments.csv')
doctors_path = os.path.join(BASE_DIR, 'doctors.csv')

doctors_available = 3
avg_consult_time = 15  # minutes per patient

def get_merged_df():
    appointments_df = pd.read_csv(appointments_path)
    appointments_df = clean_and_prepare_data(appointments_df)
    appointments_df = apply_severity(appointments_df)

    treatments_df = pd.read_csv(treatments_path)
    treatments_df.rename(columns={
        'PatientID': 'patient_id',
        'TreatmentID': 'treatment_id',
        'Description': 'description',
        'Type': 'treatment_type',
        'Date': 'treatment_date'
    }, inplace=True)

    merged = appointments_df.merge(
        treatments_df[['appointment_id', 'treatment_id', 'description', 'treatment_type', 'treatment_date']],
        on='appointment_id', how='left'
    )
    return merged

def safe_save_csv(df, path):
    """Save CSV atomically to reduce corruption risk."""
    try:
        with file_lock(path):
            tmp_path = path + ".tmp"
            backup_path = path + ".bak"
            df.to_csv(tmp_path, index=False)
            if os.path.exists(path):
                try:
                    os.replace(path, backup_path)
                except Exception:
                    pass
            os.replace(tmp_path, path)
            _highlight_log("FILE 🔐", f"Safe write completed for {os.path.basename(path)}")
    except Exception as e:
        print(f"Error saving CSV {path}: {e}")

def build_two_queue_context(doctor_id=None):
    merged_df = get_merged_df()
    
    # Filter by doctor_id if provided
    if doctor_id is not None:
        if 'doctor_id' in merged_df.columns:
            merged_df = merged_df[merged_df['doctor_id'].astype(str) == str(doctor_id)].copy()
    
    # Filter to only show scheduled and in-session appointments in the queue
    # This ensures only active appointments are shown
    if 'status' in merged_df.columns:
        status_filter = merged_df['status'].astype(str).str.lower().isin(['scheduled', 'in-session'])
        merged_df = merged_df[status_filter].copy()
    
    total_patients = merged_df['patient_id'].nunique()
    active_consultations = merged_df[merged_df['status'].str.lower() == 'in-session']['patient_id'].nunique()

    # Drop duplicate patients and ensure ordering by appointment time
    merged_df = merged_df.sort_values(by=['appointment_datetime'], ascending=True)
    merged_df = merged_df.drop_duplicates(subset='patient_id', keep='first').copy()

    # Define priority vs FCFS
    priority_df = merged_df[merged_df['Severity_Score'].isin([1, 2])].copy()
    fcfs_df = merged_df[~merged_df['Severity_Score'].isin([1, 2])].copy()

    # Within each queue, order by appointment time (FCFS within priority group as well)
    priority_df = priority_df.sort_values('appointment_datetime')
    fcfs_df = fcfs_df.sort_values('appointment_datetime')

    # Compute patients ahead and estimated wait for each queue independently
    for qdf in (priority_df, fcfs_df):
        qdf["Patients_Ahead"] = range(len(qdf))
        qdf["Estimated_Wait_Time"] = [
            pa * avg_consult_time // doctors_available for pa in qdf["Patients_Ahead"]
        ]

    queues = {
        'priority': priority_df.to_dict(orient='records'),
        'fcfs': fcfs_df.to_dict(orient='records'),
    }

    counts = {
        'priority': len(queues['priority']),
        'fcfs': len(queues['fcfs'])
    }

    return queues, total_patients, active_consultations, counts

def select_next_patient(queues):
    """Return the next scheduled patient's appointment_id from priority else FCFS."""
    def find_in_queue(q):
        for item in q:
            status = str(item.get('status', '')).lower()
            if status == 'scheduled':
                app_id = item.get('appointment_id')
                # Only return if appointment_id exists and is not None/empty
                if app_id and str(app_id).strip():
                    return str(app_id).strip()
        return None

    app_id = find_in_queue(queues.get('priority', []))
    if app_id:
        return app_id
    return find_in_queue(queues.get('fcfs', []))

# -------- OTP helpers (simulated) --------
import random

def generate_otp(length: int = 6) -> str:
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def send_otp_sms(otp: str, mobile: str):
    """Send OTP via SMS using Twilio - Real-time SMS delivery like banks"""
    try:
        from otp_config import SMS_CONFIG
        
        # Check if Twilio is configured
        if not SMS_CONFIG['enabled'] or SMS_CONFIG.get('account_sid') == 'your_twilio_account_sid' or SMS_CONFIG.get('account_sid', '').strip() == '':
            print(f"\n{'='*60}")
            print(f"[SMS DEMO MODE] OTP {otp} would be sent to {mobile}")
            print(f"[SMS DEMO MODE] Message: Your OTP is: {otp}")
            print(f"{'='*60}")
            print(f"[INFO] To enable REAL SMS (like banks):")
            print(f"  1. Sign up at https://www.twilio.com (FREE trial with $15 credit)")
            print(f"  2. Get your Account SID, Auth Token, and Phone Number")
            print(f"  3. Update otp_config.py with your credentials")
            print(f"  4. Run: pip install twilio")
            print(f"  5. See TWILIO_QUICK_SETUP.md for detailed instructions")
            print(f"{'='*60}\n")
            # Return True but note it's demo mode
            return True
        
        # Real SMS sending with Twilio
        try:
            from twilio.rest import Client
        except ImportError:
            print(f"\n{'='*60}")
            print(f"[ERROR] Twilio library not installed!")
            print(f"[FIX] Run: pip install twilio")
            print(f"{'='*60}\n")
            return False
        
        # Ensure mobile number has country code
        original_mobile = mobile
        if not mobile.startswith('+'):
            # Add +91 for India if no country code (10 digits)
            if len(mobile) == 10:
                mobile = f'+91{mobile}'
            else:
                mobile = f'+{mobile}'
        
        # Validate Twilio credentials
        if not SMS_CONFIG.get('auth_token') or SMS_CONFIG.get('auth_token') == 'your_twilio_auth_token':
            print(f"\n{'='*60}")
            print(f"[ERROR] Twilio Auth Token not configured!")
            print(f"[FIX] Update otp_config.py with your Twilio credentials")
            print(f"{'='*60}\n")
            return False
        
        if not SMS_CONFIG.get('from_number') or SMS_CONFIG.get('from_number') == '+1234567890':
            print(f"\n{'='*60}")
            print(f"[ERROR] Twilio Phone Number not configured!")
            print(f"[FIX] Update otp_config.py with your Twilio phone number")
            print(f"{'='*60}\n")
            return False
        
        # Create Twilio client and send SMS
        client = Client(SMS_CONFIG['account_sid'], SMS_CONFIG['auth_token'])
        
        # Create the message
        message_body = f'🏥 CareQueue Hospital\n\nYour OTP is: {otp}\n\nValid for 10 minutes.\n\nDo not share this code with anyone.'
        
        message = client.messages.create(
            body=message_body,
            from_=SMS_CONFIG['from_number'],
            to=mobile
        )
        
        # Success!
        print(f"\n{'='*60}")
        print(f"[✅ SMS SENT SUCCESSFULLY]")
        print(f"   📱 To: {mobile}")
        print(f"   🔑 OTP: {otp}")
        print(f"   📨 Message SID: {message.sid}")
        print(f"   📊 Status: {message.status}")
        print(f"{'='*60}\n")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n{'='*60}")
        print(f"[❌ SMS ERROR] Failed to send OTP to {mobile}")
        print(f"   Error: {error_msg}")
        print(f"{'='*60}")
        
        # Provide helpful error messages
        if 'Invalid' in error_msg or 'not a valid' in error_msg.lower():
            print(f"[FIX] Check phone number format. Use country code (e.g., +91 for India)")
        elif 'Authentication' in error_msg or 'credential' in error_msg.lower():
            print(f"[FIX] Check your Twilio Account SID and Auth Token in otp_config.py")
        elif 'Trial' in error_msg or 'verified' in error_msg.lower():
            print(f"[FIX] For trial accounts, verify the phone number in Twilio Console")
            print(f"      Go to: Phone Numbers → Verified Caller IDs")
        else:
            print(f"[FIX] Check TWILIO_QUICK_SETUP.md for setup instructions")
        print(f"{'='*60}\n")
        return False

def send_otp_email(otp: str, email: str):
    """Send OTP via Email using SMTP"""
    try:
        from otp_config import EMAIL_CONFIG
        
        if not EMAIL_CONFIG['enabled']:
            print(f"[EMAIL DEMO] OTP {otp} would be sent to {email}")
            print(f"[EMAIL DEMO] Subject: Appointment Booking OTP")
            print(f"[EMAIL DEMO] Content: Your OTP is {otp}")
            return True
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Use configuration
        smtp_server = EMAIL_CONFIG['smtp_server']
        smtp_port = EMAIL_CONFIG['smtp_port']
        sender_email = EMAIL_CONFIG['sender_email']
        sender_password = EMAIL_CONFIG['sender_password']
        
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Appointment Booking OTP"
        message["From"] = sender_email
        message["To"] = email
        
        # Create HTML content
        html = f"""
        <html>
          <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
              <h2 style="color: #4f3cc9;">Hospital Appointment Booking</h2>
              <p>Your OTP for appointment booking is:</p>
              <div style="background: #f8f9fa; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                <h1 style="color: #4f3cc9; font-size: 32px; margin: 0; letter-spacing: 5px;">{otp}</h1>
              </div>
              <p>This OTP is valid for 10 minutes. Please do not share it with anyone.</p>
              <p style="color: #666; font-size: 14px;">If you didn't request this OTP, please ignore this email.</p>
            </div>
          </body>
        </html>
        """
        
        # Attach HTML content
        html_part = MIMEText(html, "html")
        message.attach(html_part)
        
        # Send real email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, message.as_string())
        server.quit()
        
        print(f"[EMAIL] OTP {otp} sent to {email}")
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def simulate_send_otp(otp: str, destination: str):
    """Send OTP via appropriate channel based on destination"""
    if "@" in destination:
        return send_otp_email(otp, destination)
    else:
        return send_otp_sms(otp, destination)

@app.route('/')
def index():
    queues, total_patients, active_consultations, counts = build_two_queue_context()

    return render_template(
        'index.html',
        queues=queues,
        total_patients=total_patients,
        active_consultations=active_consultations,
        severity_counts=counts
    )

from flask import flash

@app.route('/add_patient', methods=['POST'])
def add_patient():
    with appointment_guard(context_label="add_patient"):
        appointments_df = pd.read_csv(appointments_path)
        treatments_df = pd.read_csv(treatments_path)
        treatments_df.rename(columns={
            'PatientID': 'patient_id',
            'TreatmentID': 'treatment_id',
            'Description': 'description',
            'Type': 'treatment_type',
            'Date': 'treatment_date'
        }, inplace=True)

        is_existing = request.form.get('is_existing')
        reason_for_visit = request.form.get('reason_for_visit', '').strip()
        description = reason_for_visit or 'routine'
        new_type = "Updated"

        if is_existing == "yes":
            patient_id = request.form.get('existing_patient_id')
            if patient_id in appointments_df['patient_id'].astype(str).values:
                appointments_df.loc[appointments_df['patient_id'] == patient_id, ['reason_for_visit', 'status']] = [
                    reason_for_visit, "Scheduled"
                ]
                appointments_df = apply_severity(appointments_df)

                app_ids = appointments_df[appointments_df['patient_id'] == patient_id]['appointment_id']
                for app_id in app_ids:
                    treatments_df.loc[treatments_df['appointment_id'] == app_id, 'description'] = description
                    treatments_df.loc[treatments_df['appointment_id'] == app_id, 'treatment_type'] = new_type
                    appointments_df.loc[appointments_df['appointment_id'] == app_id, 'status'] = 'Scheduled'

                flash(f"Patient {patient_id} updated successfully!", "success")
            else:
                flash("⚠️ Existing patient ID not found!", "danger")
                return redirect(url_for('index'))

        else:
            patient_id = request.form.get('patient_id', '').strip()
            appointment_id = request.form.get('appointment_id', '').strip()
            appointment_date = request.form.get('appointment_date', '').strip()
            appointment_time = request.form.get('appointment_time', '').strip()
            doctor_id = request.form.get('doctor_id', '').strip()

            # Validation
            if not all([patient_id, appointment_id, appointment_date, appointment_time]):
                flash("⚠️ Please fill in all required fields!", "danger")
                return redirect(url_for('index'))
            
            # Check if appointment ID already exists
            if appointment_id in appointments_df['appointment_id'].astype(str).values:
                flash(f"⚠️ Appointment ID {appointment_id} already exists! Please use a different ID.", "danger")
                return redirect(url_for('index'))
            
            # Check if patient exists in patients.csv (optional validation)
            patients_path = os.path.join(BASE_DIR, 'patients.csv')
            if os.path.exists(patients_path):
                patients_df = pd.read_csv(patients_path)
                if patient_id not in patients_df['patient_id'].astype(str).values:
                    flash(f"⚠️ Patient ID {patient_id} not found in patient records. Please register the patient first or use an existing patient ID.", "warning")
                    # Still allow creation but warn user
            
            # Auto-assign doctor if not provided
            if not doctor_id:
                doctors_df = pd.read_csv(doctors_path)
                if not doctors_df.empty:
                    # Round-robin assignment
                    existing_appointments = appointments_df[appointments_df['doctor_id'].notna()]
                    if not existing_appointments.empty:
                        last_doctor = existing_appointments['doctor_id'].iloc[-1]
                        try:
                            last_idx = doctors_df[doctors_df['doctor_id'] == last_doctor].index[0]
                            next_idx = (last_idx + 1) % len(doctors_df)
                            doctor_id = doctors_df.iloc[next_idx]['doctor_id']
                        except:
                            doctor_id = doctors_df.iloc[0]['doctor_id']
                    else:
                        doctor_id = doctors_df.iloc[0]['doctor_id']

            new_row = {
                "patient_id": patient_id,
                "appointment_id": appointment_id,
                "doctor_id": doctor_id,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time,
                "reason_for_visit": reason_for_visit,
                "status": "Scheduled"
            }

            appointments_df = pd.concat([appointments_df, pd.DataFrame([new_row])], ignore_index=True)
            appointments_df = clean_and_prepare_data(appointments_df)
            appointments_df = apply_severity(appointments_df)

            new_treatment_row = {
                "appointment_id": appointment_id,
                "treatment_id": f"T{len(treatments_df) + 1:04d}",
                "description": description,
                "treatment_type": "Initial",
                "treatment_date": appointment_date
            }
            treatments_df = pd.concat([treatments_df, pd.DataFrame([new_treatment_row])], ignore_index=True)

            flash(f"✅ Appointment {appointment_id} created successfully for Patient {patient_id}!", "success")
            
            # Send IPC notification to doctor about new appointment
            try:
                # Get patient and doctor names for notification
                patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
                doctors_df = pd.read_csv(doctors_path)
                
                patient_row = patients_df[patients_df['patient_id'].astype(str) == str(patient_id)]
                doctor_row = doctors_df[doctors_df['doctor_id'].astype(str) == str(doctor_id)]
                
                patient_name = f"{patient_row.iloc[0]['first_name']} {patient_row.iloc[0]['last_name']}" if not patient_row.empty else f"Patient {patient_id}"
                doctor_name = f"Dr. {doctor_row.iloc[0]['first_name']} {doctor_row.iloc[0]['last_name']}" if not doctor_row.empty else f"Doctor {doctor_id}"
                
                # Create notification for doctor
                notification_title = f"New Appointment: {patient_name}"
                notification_message = f"New appointment scheduled for {patient_name} on {appointment_date} at {appointment_time}. Reason: {reason_for_visit}"
                create_notification(
                    recipient_type='doctor',
                    recipient_id=doctor_id,
                    notification_type='appointment',
                    title=notification_title,
                    message=notification_message,
                    report_id=None,
                    is_read=False
                )
                
                # Publish IPC event for appointment booking
                ipc_payload = {
                    'appointment_id': appointment_id,
                    'patient_id': patient_id,
                    'patient_name': patient_name,
                    'doctor_id': doctor_id,
                    'doctor_name': doctor_name,
                    'appointment_date': appointment_date,
                    'appointment_time': appointment_time,
                    'reason_for_visit': reason_for_visit,
                    'status': 'Scheduled',
                    'timestamp': datetime.now().isoformat()
                }
                publish_ipc_event('appointment.booked', ipc_payload)
                _highlight_log("IPC ⚡", f"Appointment {appointment_id} booked for Dr. {doctor_name} - broadcast over IPC")
                
            except Exception as e:
                print(f"Error sending appointment notification via IPC: {e}")
                # Don't fail the booking if notification fails
                pass

        # Save updates using safe_save_csv for thread safety
        safe_save_csv(appointments_df, appointments_path)
        safe_save_csv(treatments_df, treatments_path)

        # Force redirect to reload data freshly
        return redirect(url_for('index', _external=True, _scheme='http'))

@app.route('/start_consultation', methods=['POST'])
def start_consult():
    appointment_id = request.form['appointment_id']
    doctor_id = request.form.get('doctor_id', '')
    with appointment_guard(appointment_id, context_label="start_consultation"):
        appointments_df = pd.read_csv(appointments_path)
        appointments_df = start_consultation(appointments_df, appointment_id)
        safe_save_csv(appointments_df, appointments_path)
    flash('Status updated: Consultation started', 'success')
    if doctor_id:
        return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
    return redirect(url_for('index'))

@app.route('/doctor/<doctor_id>')
def doctor_dashboard(doctor_id):
    # Reuse the two-queue context as the main dashboard, filtered by doctor_id
    queues, total_patients, active_consultations, severity_counts = build_two_queue_context(doctor_id=doctor_id)
    mutex_snapshot = get_mutex_snapshot()

    # Get doctor information
    doctor_info = {}
    if os.path.exists(doctors_path):
        try:
            doctors_df = pd.read_csv(doctors_path)
            doctor = doctors_df[doctors_df['doctor_id'].astype(str) == str(doctor_id)]
            if not doctor.empty:
                doctor_info = {
                    'doctor_id': doctor_id,
                    'first_name': doctor.iloc[0].get('first_name', ''),
                    'last_name': doctor.iloc[0].get('last_name', ''),
                    'specialization': doctor.iloc[0].get('specialization', ''),
                    'hospital_branch': doctor.iloc[0].get('hospital_branch', ''),
                    'years_experience': doctor.iloc[0].get('years_experience', ''),
                    'email': doctor.iloc[0].get('email', ''),
                    'phone_number': doctor.iloc[0].get('phone_number', '')
                }
                # Create full name
                doctor_info['full_name'] = f"Dr. {doctor_info['first_name']} {doctor_info['last_name']}".strip()
        except Exception as e:
            print(f"Error loading doctor info: {e}")
            doctor_info = {'doctor_id': doctor_id, 'full_name': f'Doctor {doctor_id}'}

    # Optional: include lab reports for this doctor if file exists
    reports = []
    lab_path = os.path.join(BASE_DIR, 'labreport.csv')
    if os.path.exists(lab_path):
        try:
            df = pd.read_csv(lab_path)
            if 'doctor_id' in df.columns:
                doctor_reports = df[df['doctor_id'].astype(str) == str(doctor_id)]
                reports = doctor_reports.to_dict(orient='records')
        except Exception as e:
            print("Error reading labreport.csv:", e)
    
    # Get unread notifications for doctor
    notifications = get_notifications('doctor', doctor_id, unread_only=True)

    return render_template(
        'doctor_dashboard.html',
        doctor_id=doctor_id,
        doctor_info=doctor_info,
        queues=queues,
        total_patients=total_patients,
        active_consultations=active_consultations,
        severity_counts=severity_counts,
        reports=reports,
        notifications=notifications,
        mutex_snapshot=mutex_snapshot
    )

@app.route('/patient/<patient_id>/details')
def patient_details_api(patient_id):
    """API endpoint to get patient details"""
    try:
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        patient = patients_df[patients_df['patient_id'].astype(str) == str(patient_id)]
        
        if patient.empty:
            return {'success': False, 'message': 'Patient not found'}, 404
        
        patient_data = patient.iloc[0].to_dict()
        return {'success': True, 'patient': patient_data}
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

@app.route('/patient/<patient_id>')
def patient_dashboard(patient_id):
    import os
    import pandas as pd
    from datetime import datetime, date

    # --- Patient Info ---
    patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
    patient_info = patients_df[patients_df['patient_id'].astype(str) == str(patient_id)]
    if patient_info.empty:
        flash("Patient not found!", "danger")
        return redirect(url_for('index'))
    patient_info = patient_info.iloc[0].to_dict()

    # --- Appointments ---
    appointments_df = pd.read_csv(appointments_path)
    doctors_dict = {}
    try:
        doctors_df = pd.read_csv(doctors_path)
        doctors_dict = dict(zip(doctors_df['doctor_id'], doctors_df['first_name'] + ' ' + doctors_df['last_name']))
    except Exception as e:
        print("Error loading doctors data:", e)
    appointments_df['doctor_name'] = appointments_df['doctor_id'].map(doctors_dict).fillna('Unknown Doctor')
    patient_appointments_df = appointments_df[appointments_df['patient_id'].astype(str) == str(patient_id)]

    today = date.today()
    upcoming_appointments = []
    recent_appointments = []
    completed_appointments = []
    for _, row in patient_appointments_df.iterrows():
        item = row.to_dict()
        appt_date = pd.to_datetime(item.get('appointment_date', item.get('date', '')), errors='coerce')
        item['appointment_date'] = appt_date.strftime('%Y-%m-%d') if appt_date is not pd.NaT else ""
        item['appointment_time'] = item.get('appointment_time', item.get('time', ''))
        status_lower = item.get('status', '').lower()
        
        # Fixed logic: upcoming = future date OR today/future with scheduled/in-session status
        if status_lower == 'completed':
            completed_appointments.append(item)
        elif appt_date is not pd.NaT and appt_date.date() >= today and status_lower in ['scheduled', 'in-session']:
            # Future or today appointments that are scheduled
            upcoming_appointments.append(item)
        else:
            # Past appointments or other statuses go to recent
            recent_appointments.append(item)
    # Sort appointments
    upcoming_appointments.sort(key=lambda x: (x.get('appointment_date', ''), x.get('appointment_time', '')))
    recent_appointments.sort(key=lambda x: x.get('appointment_date', ''), reverse=True)
    completed_appointments.sort(key=lambda x: x.get('appointment_date', ''), reverse=True)

    # --- Treatments ---
    treatments = []
    try:
        treatments_df = pd.read_csv(treatments_path)
        treatments_with_patient = treatments_df.merge(
            appointments_df[['appointment_id', 'patient_id']],
            on='appointment_id',
            how='left'
        )
        ptreat = treatments_with_patient[treatments_with_patient['patient_id'].astype(str) == str(patient_id)]
        if not ptreat.empty:
            treatments = ptreat.sort_values('treatment_date', ascending=False).to_dict(orient='records')
    except Exception as e:
        print("Error loading treatments data:", e)

    # --- Billing ---
    bills = []
    paid_amount = 0
    pending_amount = 0
    failed_amount = 0
    billing_path = os.path.join(BASE_DIR, 'billing.csv')
    if os.path.exists(billing_path):
        try:
            billing_df = pd.read_csv(billing_path)
            ptbills = billing_df[billing_df['patient_id'].astype(str) == str(patient_id)]
            for _, row in ptbills.iterrows():
                b = row.to_dict()
                status = b.get('payment_status', b.get('status', '')).capitalize()
                b['payment_status'] = status
                bills.append(b)
                amt = float(b.get('amount', 0))
                if status == 'Paid':
                    paid_amount += amt
                elif status == 'Pending':
                    pending_amount += amt
                elif status == 'Failed':
                    failed_amount += amt
            bills.sort(key=lambda x: x['bill_date'], reverse=True)
        except Exception as e:
            print("Error loading billing data:", e)
    pending_bills = [b for b in bills if b.get('payment_status', '') == 'Pending']

    # --- Lab Reports ---
    lab_reports = []
    lab_path = os.path.join(BASE_DIR, 'labreport.csv')
    if os.path.exists(lab_path):
        try:
            lab_df = pd.read_csv(lab_path)
            filtered_lab = lab_df[lab_df['patient_id'].astype(str) == str(patient_id)]
            if not filtered_lab.empty:
                if 'status' not in filtered_lab.columns:
                    filtered_lab['status'] = 'new'
                if 'file_path' not in filtered_lab.columns:
                    filtered_lab['file_path'] = None
                # 'date' used for generic report date.
                datecol = 'test_date' if 'test_date' in filtered_lab.columns else 'date'
                filtered_lab = filtered_lab.sort_values(datecol, ascending=False)
                lab_reports = filtered_lab.to_dict(orient='records')
        except Exception as e:
            print("Error loading lab reports:", e)

    # --- Medications & Allergies (You can fetch from DB; below is mock) ---
    medications = [
        {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'Twice daily', 'prescribed_date': '2023-10-01', 'status': 'Active'}
    ]
    allergies = [
        {'allergen': 'Penicillin', 'severity': 'Severe', 'reaction': 'Rash and difficulty breathing'}
    ]

    # Defensive for template fields
    for key in ['contact_number', 'date_of_birth', 'address', 'insurance_provider', 'email', 'emergency_contact']:
        if key not in patient_info:
            patient_info[key] = ""

    # Get unread notifications for patient
    notifications = get_notifications('patient', patient_id, unread_only=True)
    
    return render_template(
        'patient_dashboard.html',
        patient_info=patient_info,
        upcoming_appointments=upcoming_appointments,
        recent_appointments=recent_appointments,
        completed_appointments=completed_appointments,
        pending_bills=pending_bills,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        failed_amount=failed_amount,
        bills=bills,
        treatments=treatments,
        lab_reports=lab_reports,
        medications=medications,
        allergies=allergies,
        notifications=notifications
    )

@app.route('/book', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        step = request.form.get('step', 'start')
        
        if step == 'start':
            # Step 1: Collect mobile number and send OTP
            mobile = request.form.get('mobile', '').strip()
            
            # Check if patient was found via lookup
            if 'lookup_patient' in session:
                patient = session['lookup_patient']
                mobile = patient.get('contact_number', mobile)
                session.pop('lookup_patient', None)
            elif not mobile:
                flash('Please provide your mobile number.', 'danger')
                return render_template('book.html', step=1)
            else:
                # Look up patient by mobile number
                patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
                patient = None
                
                # Try to find patient by mobile
                mobile_match = patients_df[patients_df['contact_number'].astype(str) == str(mobile)]
                
                if not mobile_match.empty:
                    patient = mobile_match.iloc[0].to_dict()
                else:
                    # Patient not found
                    flash('Patient not found. Please register first or check your details.', 'warning')
                    return redirect(url_for('register_patient'))
            
            # Generate and send OTP
            otp = generate_otp()
            try:
                session['booking_mobile'] = mobile
                session['booking_otp'] = otp
                session['booking_patient'] = patient
            except Exception as e:
                print(f"Session error: {e}")
            
            # Send OTP via SMS (real SMS sending)
            send_otp_sms(otp, mobile)
            
            flash('OTP sent to your mobile number. Please check and verify.', 'success')
            return render_template('book.html', step=2, debug_otp=otp)
            
        elif step == 'verify':
            # Step 2: Verify OTP
            code = request.form.get('otp', '').strip()
            
            if not code or 'booking_otp' not in session:
                flash('Invalid OTP session. Please request a new OTP.', 'danger')
                return render_template('book.html', step=1)
            
            if code != session.get('booking_otp'):
                flash('Incorrect OTP. Please try again.', 'danger')
                return render_template('book.html', step=2, debug_otp=session.get('booking_otp'))
            
            # OTP verified - proceed to doctor selection
            session['booking_verified'] = True
            patient_info = session.get('booking_patient')
            
            # Load doctors
            doctors = []
            try:
                doctors_df = pd.read_csv(doctors_path)
                doctors = doctors_df.to_dict(orient='records')
            except Exception as e:
                print("Error loading doctors:", e)
            
            from datetime import date
            today = date.today().strftime('%Y-%m-%d')
            
            flash('OTP verified successfully! Please select your doctor and time slot.', 'success')
            return render_template('book.html', step=3, patient_info=patient_info, doctors=doctors, today=today)
            
        elif step == 'finish':
            # Step 3: Complete booking
            if not session.get('booking_verified'):
                flash('Please verify OTP first.', 'warning')
                return render_template('book.html', step=1)
            
            patient_info = session.get('booking_patient')
            if not patient_info:
                flash('Session expired. Please start again.', 'danger')
                return render_template('book.html', step=1)
            
            # Get form data
            patient_id = patient_info['patient_id']
            appointment_date = request.form.get('appointment_date', '').strip()
            appointment_time = request.form.get('appointment_time', '').strip()
            reason_for_visit = request.form.get('reason_for_visit', '').strip() or 'General Consultation'
            doctor_id = request.form.get('doctor_id', '').strip()
            
            if not all([appointment_date, appointment_time, doctor_id]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('book.html', step=3, patient_info=patient_info, doctors=doctors, today=date.today().strftime('%Y-%m-%d'))
            
            # Check for conflicts - entire operation must be atomic within the lock
            # Use descriptive context that includes patient and doctor info for mutex monitor
            context_label = f"book_appointment_patient_{patient_id}_doctor_{doctor_id}"
            with appointment_guard(context_label=context_label):
                # Read both dataframes inside the lock to ensure consistency
                appointments_df = pd.read_csv(appointments_path)
                appointments_df = clean_and_prepare_data(appointments_df)
                treatments_df = pd.read_csv(treatments_path)
                
                is_conflict = False
                if 'doctor_id' in appointments_df.columns:
                    try:
                        subset = appointments_df[
                            (appointments_df['doctor_id'].astype(str) == doctor_id)
                            & (appointments_df['appointment_date'].astype(str) == appointment_date)
                            & (appointments_df['appointment_time'].astype(str) == appointment_time)
                            & (appointments_df['status'].astype(str).str.lower().isin(['scheduled', 'in-session']))
                        ]
                        is_conflict = not subset.empty
                    except Exception as e:
                        print(f"Conflict check error: {e}")
                        is_conflict = True
                
                if is_conflict:
                    flash('Selected time slot is already booked. Please choose another time.', 'danger')
                    # Need to reload doctors for the template
                    doctors = []
                    try:
                        doctors_df = pd.read_csv(doctors_path)
                        doctors = doctors_df.to_dict(orient='records')
                    except Exception as e:
                        print("Error loading doctors:", e)
                    return render_template('book.html', step=3, patient_info=patient_info, doctors=doctors, today=date.today().strftime('%Y-%m-%d'))
                
                # Generate unique appointment ID
                existing_ids = set(appointments_df.get('appointment_id', pd.Series(dtype=str)).astype(str).values)
                base_num = len(existing_ids) + 1
                new_id = f"A{base_num:04d}"
                while new_id in existing_ids:
                    base_num += 1
                    new_id = f"A{base_num:04d}"
                
                # Create appointment
                new_appointment = {
                    'patient_id': patient_id,
                    'appointment_id': new_id,
                    'appointment_date': appointment_date,
                    'appointment_time': appointment_time,
                    'reason_for_visit': reason_for_visit,
                    'status': 'Scheduled',
                    'doctor_id': doctor_id
                }
                
                appointments_df = pd.concat([appointments_df, pd.DataFrame([new_appointment])], ignore_index=True)
                appointments_df = clean_and_prepare_data(appointments_df)
                appointments_df = apply_severity(appointments_df)
                
                # Create treatment record (inside the lock)
                new_treatment = {
                    'appointment_id': new_id,
                    'treatment_id': f"T{len(treatments_df) + 1:04d}",
                    'description': reason_for_visit,
                    'treatment_type': 'Initial',
                    'treatment_date': appointment_date,
                    'cost': 0  # Will be calculated later
                }
                treatments_df = pd.concat([treatments_df, pd.DataFrame([new_treatment])], ignore_index=True)
                
                # Save data atomically (both files saved within the lock)
                safe_save_csv(appointments_df, appointments_path)
                safe_save_csv(treatments_df, treatments_path)
                
                # Send IPC notification to doctor about new appointment
                try:
                    # Get patient and doctor names for notification
                    patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
                    doctors_df = pd.read_csv(doctors_path)
                    
                    patient_row = patients_df[patients_df['patient_id'].astype(str) == str(patient_id)]
                    doctor_row = doctors_df[doctors_df['doctor_id'].astype(str) == str(doctor_id)]
                    
                    patient_name = f"{patient_row.iloc[0]['first_name']} {patient_row.iloc[0]['last_name']}" if not patient_row.empty else f"Patient {patient_id}"
                    doctor_name = f"Dr. {doctor_row.iloc[0]['first_name']} {doctor_row.iloc[0]['last_name']}" if not doctor_row.empty else f"Doctor {doctor_id}"
                    
                    # Create notification for doctor
                    notification_title = f"New Appointment: {patient_name}"
                    notification_message = f"New appointment scheduled for {patient_name} on {appointment_date} at {appointment_time}. Reason: {reason_for_visit}"
                    create_notification(
                        recipient_type='doctor',
                        recipient_id=doctor_id,
                        notification_type='appointment',
                        title=notification_title,
                        message=notification_message,
                        report_id=None,
                        is_read=False
                    )
                    
                    # Publish IPC event for appointment booking
                    ipc_payload = {
                        'appointment_id': new_id,
                        'patient_id': patient_id,
                        'patient_name': patient_name,
                        'doctor_id': doctor_id,
                        'doctor_name': doctor_name,
                        'appointment_date': appointment_date,
                        'appointment_time': appointment_time,
                        'reason_for_visit': reason_for_visit,
                        'status': 'Scheduled',
                        'timestamp': datetime.now().isoformat()
                    }
                    publish_ipc_event('appointment.booked', ipc_payload)
                    _highlight_log("IPC ⚡", f"Appointment {new_id} booked for Dr. {doctor_name} - broadcast over IPC")
                    
                except Exception as e:
                    print(f"Error sending appointment notification via IPC: {e}")
                    # Don't fail the booking if notification fails
                    pass
            
            # Get doctor name for confirmation
            doctors_df = pd.read_csv(doctors_path)
            doctor_info = doctors_df[doctors_df['doctor_id'] == doctor_id]
            doctor_name = f"{doctor_info.iloc[0]['first_name']} {doctor_info.iloc[0]['last_name']}" if not doctor_info.empty else "Unknown Doctor"
            
            # Clear session
            try:
                session.pop('booking_verified', None)
                session.pop('booking_otp', None)
                session.pop('booking_mobile', None)
                session.pop('booking_email', None)
                session.pop('booking_patient', None)
            except Exception:
                pass
            
            # Get full patient info for view details
            patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
            full_patient = patients_df[patients_df['patient_id'].astype(str) == str(patient_id)]
            patient_details = full_patient.iloc[0].to_dict() if not full_patient.empty else patient_info
            
            # Show confirmation
            return render_template('book.html', 
                                 step=4,
                                 appointment_id=new_id,
                                 appointment_date=appointment_date,
                                 appointment_time=appointment_time,
                                 doctor_name=doctor_name,
                                 patient_name=f"{patient_info['first_name']} {patient_info['last_name']}",
                                 patient_id=patient_id,
                                 patient_details=patient_details)
        
        # Unknown step
        return render_template('book.html', step=1)
    
    # GET request - show initial form
    return render_template('book.html', step=1)

@app.route('/doctor/schedule')
def doctor_schedule():
    # requires OTP verified
    if not session.get('booking_verified'):
        flash('Please verify OTP first.', 'warning')
        return redirect(url_for('book_appointment'))

    # Load doctors and existing appointments to compute simple availability
    doctors = []
    try:
        if os.path.exists(doctors_path):
            ddf = pd.read_csv(doctors_path)
            # Expect at least doctor_id and name columns
            doc_cols = [c for c in ddf.columns]
            for _, row in ddf.iterrows():
                doctors.append({k: row[k] for k in doc_cols if k in row})
    except Exception as e:
        print('Error loading doctors.csv:', e)

    return render_template('doctor_schedule.html', doctors=doctors)

@app.route('/complete_consultation', methods=['POST'])
def complete_consult():
    appointment_id = request.form['appointment_id']
    doctor_id = request.form.get('doctor_id', '')
    with appointment_guard(appointment_id, context_label="complete_consultation"):
        appointments_df = pd.read_csv(appointments_path)
        appointments_df = complete_consultation(appointments_df, appointment_id)
        safe_save_csv(appointments_df, appointments_path)
    flash('Status updated: Consultation completed', 'success')
    if doctor_id:
        return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
    return redirect(url_for('index'))

@app.route('/call_next', methods=['POST'])
def call_next():
    doctor_id = request.form.get('doctor_id', '')
    # Build current queues
    queues, _, _, _ = build_two_queue_context()
    next_app_id = select_next_patient(queues)
    
    if not next_app_id:
        flash("No scheduled patients available to call.", "warning")
        if doctor_id:
            return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
        return redirect(url_for('index'))
    
    print(f"[CALL_NEXT] Selected appointment_id: {next_app_id}")
    
    # Update status to in-session with mutex protection
    with appointment_guard(next_app_id, context_label="call_next"):
        appointments_df = pd.read_csv(appointments_path)
        
        # Debug: Check what appointment_ids exist
        existing_ids = appointments_df['appointment_id'].astype(str).values
        print(f"[CALL_NEXT] Total appointments in CSV: {len(existing_ids)}")
        print(f"[CALL_NEXT] Sample appointment_ids: {list(existing_ids[:5])}")
        
        # Verify appointment exists before updating
        if next_app_id not in existing_ids:
            print(f"[CALL_NEXT] ERROR: Appointment {next_app_id} not found in CSV!")
            print(f"[CALL_NEXT] Available IDs include: {[id for id in existing_ids if 'A013' in str(id)]}")
            flash(f"Appointment {next_app_id} not found. It may have been cancelled or already processed.", "danger")
            if doctor_id:
                return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
            return redirect(url_for('index'))
        
        # Get patient info for better feedback
        patient_row = appointments_df[appointments_df['appointment_id'].astype(str) == str(next_app_id)]
        if patient_row.empty:
            flash(f"Appointment {next_app_id} found but patient data is missing.", "danger")
            if doctor_id:
                return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
            return redirect(url_for('index'))
        
        patient_id = patient_row.iloc[0]['patient_id']
        current_status = patient_row.iloc[0].get('status', 'unknown')
        
        print(f"[CALL_NEXT] Found appointment {next_app_id} for patient {patient_id}, current status: {current_status}")
        
        appointments_df = start_consultation(appointments_df, next_app_id)
        safe_save_csv(appointments_df, appointments_path)
        
        flash(f"Called next patient: {patient_id} (Appointment {next_app_id})", "success")
    
    if doctor_id:
        return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
    return redirect(url_for('index'))

@app.route('/patient/<patient_id>/reschedule', methods=['POST'])
def reschedule_appointment():
    patient_id = request.form.get('patient_id')
    appointment_id = request.form.get('appointment_id')
    new_date = request.form.get('new_date')
    new_time = request.form.get('new_time')
    
    if not all([patient_id, appointment_id, new_date, new_time]):
        flash("Please provide all required information.", "danger")
        return redirect(url_for('patient_dashboard', patient_id=patient_id))
    
    # Update appointment
    with appointment_guard(appointment_id, context_label="reschedule"):
        appointments_df = pd.read_csv(appointments_path)
        mask = appointments_df['appointment_id'] == appointment_id
        if mask.any():
            appointments_df.loc[mask, 'appointment_date'] = new_date
            appointments_df.loc[mask, 'appointment_time'] = new_time
            appointments_df = clean_and_prepare_data(appointments_df)
            appointments_df = apply_severity(appointments_df)
            safe_save_csv(appointments_df, appointments_path)
            flash("Appointment rescheduled successfully!", "success")
        else:
            flash("Appointment not found!", "danger")
    
    return redirect(url_for('patient_dashboard', patient_id=patient_id))

@app.route('/patient/<patient_id>/cancel', methods=['POST'])
def cancel_appointment():
    patient_id = request.form.get('patient_id')
    appointment_id = request.form.get('appointment_id')
    
    if not all([patient_id, appointment_id]):
        flash("Please provide all required information.", "danger")
        return redirect(url_for('patient_dashboard', patient_id=patient_id))
    
    # Update appointment status
    with appointment_guard(appointment_id, context_label="cancel"):
        appointments_df = pd.read_csv(appointments_path)
        mask = appointments_df['appointment_id'] == appointment_id
        if mask.any():
            appointments_df.loc[mask, 'status'] = 'Cancelled'
            safe_save_csv(appointments_df, appointments_path)
            flash("Appointment cancelled successfully!", "success")
        else:
            flash("Appointment not found!", "danger")
    
    return redirect(url_for('patient_dashboard', patient_id=patient_id))

@app.route('/patient/<patient_id>/pay_bill', methods=['POST'])
def pay_bill():
    patient_id = request.form.get('patient_id')
    bill_id = request.form.get('bill_id')
    payment_method = request.form.get('payment_method', 'Credit Card')
    
    if not all([patient_id, bill_id]):
        flash("Please provide all required information.", "danger")
        return redirect(url_for('patient_dashboard', patient_id=patient_id))
    
    # Update bill status
    billing_path = os.path.join(BASE_DIR, 'billing.csv')
    if os.path.exists(billing_path):
        billing_df = pd.read_csv(billing_path)
        mask = billing_df['bill_id'] == bill_id
        if mask.any():
            billing_df.loc[mask, 'payment_status'] = 'Paid'
            billing_df.loc[mask, 'payment_method'] = payment_method
            safe_save_csv(billing_df, billing_path)
            flash("Payment processed successfully!", "success")
        else:
            flash("Bill not found!", "danger")
    else:
        flash("Billing system not available!", "danger")
    
    return redirect(url_for('patient_dashboard', patient_id=patient_id))

@app.route('/patient/<patient_id>/update_profile', methods=['POST'])
def update_patient_profile(patient_id):
    contact_number = request.form.get('contact_number')
    email = request.form.get('email')
    address = request.form.get('address')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    gender = request.form.get('gender')
    date_of_birth = request.form.get('date_of_birth')
    insurance_provider = request.form.get('insurance_provider')
    insurance_number = request.form.get('insurance_number')

    if not patient_id:
        flash("Patient ID is required.", "danger")
        return redirect(url_for('patient_dashboard', patient_id=patient_id))
    
    # Update patient information
    patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
    mask = patients_df['patient_id'].astype(str) == str(patient_id)
    
    if mask.any():
        if contact_number:
            patients_df.loc[mask, 'contact_number'] = contact_number
        if email:
            patients_df.loc[mask, 'email'] = email
        if address:
            patients_df.loc[mask, 'address'] = address
        if first_name:
            patients_df.loc[mask, 'first_name'] = first_name
        if last_name:
            patients_df.loc[mask, 'last_name'] = last_name
        if gender:
            patients_df.loc[mask, 'gender'] = gender
        if date_of_birth:
            patients_df.loc[mask, 'date_of_birth'] = date_of_birth
        if insurance_provider:
            patients_df.loc[mask, 'insurance_provider'] = insurance_provider
        if insurance_number:
            patients_df.loc[mask, 'insurance_number'] = insurance_number

        safe_save_csv(patients_df, os.path.join(BASE_DIR, 'patients.csv'))
        flash("Profile updated successfully!", "success")
    else:
        flash("Patient not found!", "danger")
    
    return redirect(url_for('patient_dashboard', patient_id=patient_id))

@app.route('/register', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        step = request.form.get('step', 'init')
        
        if step == 'init':
            # Step 1: Get mobile number and send OTP
            contact_number = request.form.get('contact_number', '').strip()
            
            if not contact_number:
                flash('Please provide your mobile number.', 'danger')
                return render_template('register.html', step=1)
            
            # Check if patient already exists
            patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
            mobile_exists = not patients_df[patients_df['contact_number'].astype(str) == str(contact_number)].empty
            
            if mobile_exists:
                flash('A patient with this mobile number already exists. Please login instead.', 'danger')
                return render_template('register.html', step=1)
            
            # Generate and send OTP
            otp = generate_otp()
            session['register_mobile'] = contact_number
            session['register_otp'] = otp
            
            # Send OTP
            send_otp_sms(otp, contact_number)
            
            flash('OTP sent to your mobile number. Please verify to continue registration.', 'success')
            return render_template('register.html', step=2, debug_otp=otp)
        
        elif step == 'verify':
            # Step 2: Verify OTP
            otp = request.form.get('otp', '').strip()
            
            if not otp or 'register_otp' not in session:
                flash('Invalid OTP session. Please start again.', 'danger')
                return render_template('register.html', step=1)
            
            if otp != session.get('register_otp'):
                flash('Incorrect OTP. Please try again.', 'danger')
                return render_template('register.html', step=2, debug_otp=session.get('register_otp'))
            
            # OTP verified - proceed to registration form
            session['register_verified'] = True
            flash('OTP verified! Please complete your registration.', 'success')
            return render_template('register.html', step=3, mobile=session.get('register_mobile'))
        
        elif step == 'complete':
            # Step 3: Complete registration
            if not session.get('register_verified'):
                flash('Please verify OTP first.', 'danger')
                return redirect(url_for('register_patient'))
            
            # Get form data
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            gender = request.form.get('gender', '').strip()
            date_of_birth = request.form.get('date_of_birth', '').strip()
            contact_number = session.get('register_mobile', '').strip()
            email = request.form.get('email', '').strip()
            address = request.form.get('address', '').strip()
            insurance_provider = request.form.get('insurance_provider', '').strip()
            insurance_number = request.form.get('insurance_number', '').strip()
            
            # Validate required fields
            if not all([first_name, last_name, gender, date_of_birth, contact_number, email]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('register.html', step=3, mobile=contact_number)
            
            # Check if patient already exists (double check)
            patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
            mobile_exists = not patients_df[patients_df['contact_number'].astype(str) == str(contact_number)].empty
            email_exists = not patients_df[patients_df['email'].astype(str) == str(email)].empty
            
            if mobile_exists:
                flash('A patient with this mobile number already exists.', 'danger')
                return render_template('register.html', step=3, mobile=contact_number)
            
            if email_exists:
                flash('A patient with this email address already exists.', 'danger')
                return render_template('register.html', step=3, mobile=contact_number)
            
            # Generate new patient ID
            existing_ids = set(patients_df['patient_id'].astype(str).values)
            base_num = len(existing_ids) + 1
            new_patient_id = f"P{base_num:03d}"
            while new_patient_id in existing_ids:
                base_num += 1
                new_patient_id = f"P{base_num:03d}"
            
            # Create new patient record
            from datetime import datetime
            new_patient = {
                'patient_id': new_patient_id,
                'first_name': first_name,
                'last_name': last_name,
                'gender': gender,
                'date_of_birth': date_of_birth,
                'contact_number': contact_number,
                'address': address,
                'registration_date': datetime.now().strftime('%Y-%m-%d'),
                'insurance_provider': insurance_provider,
                'insurance_number': insurance_number,
                'email': email
            }
            
            # Add to patients dataframe
            patients_df = pd.concat([patients_df, pd.DataFrame([new_patient])], ignore_index=True)
            safe_save_csv(patients_df, os.path.join(BASE_DIR, 'patients.csv'))
            
            # Clear session
            session.pop('register_mobile', None)
            session.pop('register_otp', None)
            session.pop('register_verified', None)
            
            flash(f'Patient registered successfully! Patient ID: {new_patient_id}', 'success')
            return redirect(url_for('book_appointment'))
    
    return render_template('register.html', step=1)

@app.route('/lookup', methods=['GET', 'POST'])
def lookup_patient():
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        
        if not mobile and not email:
            flash('Please provide either mobile number or email address.', 'danger')
            return render_template('lookup.html')
        
        # Look up patient
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        patient = None
        
        if mobile:
            mobile_match = patients_df[patients_df['contact_number'].astype(str) == str(mobile)]
            if not mobile_match.empty:
                patient = mobile_match.iloc[0].to_dict()
        
        if not patient and email:
            email_match = patients_df[patients_df['email'].astype(str) == str(email)]
            if not email_match.empty:
                patient = email_match.iloc[0].to_dict()
        
        if patient:
            # Store patient in session and redirect to booking
            session['lookup_patient'] = patient
            flash('Patient found! You can now book an appointment.', 'success')
            return redirect(url_for('book_appointment'))
        else:
            flash('Patient not found. Please register first or check your details.', 'warning')
            return redirect(url_for('register_patient'))
    
    return render_template('lookup.html')

# IPC System for Lab Records
@app.route('/lab/send_to_doctor', methods=['POST'])
def send_lab_to_doctor():
    """Send lab records to doctor via IPC"""
    try:
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        report_id = request.form.get('report_id')
        
        if not all([patient_id, doctor_id, report_id]):
            return {'success': False, 'message': 'Missing required parameters'}
        
        # Load lab reports
        lab_df = pd.read_csv(os.path.join(BASE_DIR, 'labreport.csv'))
        report = lab_df[lab_df['report_id'] == report_id]
        
        if report.empty:
            return {'success': False, 'message': 'Report not found'}
        
        # Load doctor information
        doctors_df = pd.read_csv(doctors_path)
        doctor = doctors_df[doctors_df['doctor_id'] == doctor_id]
        
        if doctor.empty:
            return {'success': False, 'message': 'Doctor not found'}
        
        # Load patient information
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        patient = patients_df[patients_df['patient_id'] == patient_id]
        
        if patient.empty:
            return {'success': False, 'message': 'Patient not found'}
        
        # Create IPC message
        ipc_message = {
            'type': 'lab_report',
            'timestamp': pd.Timestamp.now().isoformat(),
            'patient': {
                'id': patient_id,
                'name': f"{patient.iloc[0]['first_name']} {patient.iloc[0]['last_name']}",
                'dob': patient.iloc[0]['date_of_birth']
            },
            'doctor': {
                'id': doctor_id,
                'name': f"Dr. {doctor.iloc[0]['first_name']} {doctor.iloc[0]['last_name']}",
                'specialization': doctor.iloc[0].get('specialization', 'General Medicine')
            },
            'report': {
                'id': report_id,
                'test_name': report.iloc[0]['test_name'],
                'result': report.iloc[0]['result'],
                'date': report.iloc[0]['date']
            }
        }
        
        # Send via IPC (mocked here)
        send_lab_report_ipc(ipc_message)
        
        return {'success': True, 'message': 'Lab report sent to doctor successfully'}
        
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}

def create_notification(recipient_type, recipient_id, notification_type, title, message, report_id=None, is_read=False):
    """Create a notification for doctor or patient"""
    notifications_path = os.path.join(BASE_DIR, 'notifications.csv')
    
    # Create notifications CSV if it doesn't exist
    if not os.path.exists(notifications_path):
        notifications_df = pd.DataFrame(columns=[
            'notification_id', 'recipient_type', 'recipient_id', 'notification_type',
            'title', 'message', 'report_id', 'is_read', 'created_at'
        ])
    else:
        notifications_df = pd.read_csv(notifications_path)
    
    # Generate unique notification ID
    notification_id = f"N{10000 + len(notifications_df) + 1}"
    
    new_notification = {
        'notification_id': notification_id,
        'recipient_type': recipient_type,  # 'doctor' or 'patient'
        'recipient_id': recipient_id,
        'notification_type': notification_type,  # 'lab_report', 'appointment', etc.
        'title': title,
        'message': message,
        'report_id': report_id if report_id else '',
        'is_read': is_read,
        'created_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    notifications_df = pd.concat([notifications_df, pd.DataFrame([new_notification])], ignore_index=True)
    safe_save_csv(notifications_df, notifications_path)
    
    return notification_id

def get_notifications(recipient_type, recipient_id, unread_only=False):
    """Get notifications for a doctor or patient"""
    notifications_path = os.path.join(BASE_DIR, 'notifications.csv')
    
    if not os.path.exists(notifications_path):
        return []
    
    try:
        notifications_df = pd.read_csv(notifications_path)
        filtered = notifications_df[
            (notifications_df['recipient_type'] == recipient_type) &
            (notifications_df['recipient_id'].astype(str) == str(recipient_id))
        ]
        
        if unread_only:
            filtered = filtered[filtered['is_read'].astype(str).str.lower() != 'true']
        
        # Sort by created_at descending (newest first)
        filtered = filtered.sort_values('created_at', ascending=False)
        return filtered.to_dict(orient='records')
    except Exception as e:
        print(f"Error loading notifications: {e}")
        return []

def mark_notification_read(notification_id):
    """Mark a notification as read"""
    notifications_path = os.path.join(BASE_DIR, 'notifications.csv')
    
    if not os.path.exists(notifications_path):
        return False
    
    try:
        notifications_df = pd.read_csv(notifications_path)
        notifications_df.loc[notifications_df['notification_id'] == notification_id, 'is_read'] = True
        safe_save_csv(notifications_df, notifications_path)
        return True
    except Exception as e:
        print(f"Error marking notification as read: {e}")
        return False

def send_lab_report_ipc(message):
    """Send lab report via IPC to doctor and patient - creates notifications"""
    try:
        # Get patient and doctor names
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        doctors_df = pd.read_csv(doctors_path)
        
        patient = patients_df[patients_df['patient_id'].astype(str) == str(message['patient_id'])]
        doctor = doctors_df[doctors_df['doctor_id'].astype(str) == str(message['doctor_id'])]
        
        patient_name = f"{patient.iloc[0]['first_name']} {patient.iloc[0]['last_name']}" if not patient.empty else "Unknown"
        doctor_name = f"Dr. {doctor.iloc[0]['first_name']} {doctor.iloc[0]['last_name']}" if not doctor.empty else "Unknown"
        
        # Create notification for doctor
        doctor_title = f"New Lab Report: {message['test_name']}"
        doctor_message = f"Lab report for patient {patient_name} is ready. Test: {message['test_name']}"
        create_notification(
            recipient_type='doctor',
            recipient_id=message['doctor_id'],
            notification_type='lab_report',
            title=doctor_title,
            message=doctor_message,
            report_id=message['report_id'],
            is_read=False
        )
        
        # Create notification for patient
        patient_title = f"Your Lab Report: {message['test_name']}"
        patient_message = f"Your lab test results for {message['test_name']} are now available."
        create_notification(
            recipient_type='patient',
            recipient_id=message['patient_id'],
            notification_type='lab_report',
            title=patient_title,
            message=patient_message,
            report_id=message['report_id'],
            is_read=False
        )
        
        print(f"[IPC] Notification sent to Dr. {doctor_name} (ID: {message['doctor_id']})")
        print(f"[IPC] Notification sent to Patient {patient_name} (ID: {message['patient_id']})")
        print(f"[IPC] Report ID: {message['report_id']}")

        ipc_payload = {
            'report_id': message['report_id'],
            'test_name': message['test_name'],
            'patient_id': message['patient_id'],
            'patient_name': patient_name,
            'doctor_id': message['doctor_id'],
            'doctor_name': doctor_name,
            'priority': message.get('priority', 'Normal'),
            'status': message.get('status', 'Pending'),
            'timestamp': message.get('timestamp', pd.Timestamp.now().isoformat())
        }
        publish_ipc_event('lab_report', ipc_payload)
        _highlight_log("IPC ⚡", f"Lab report {message['report_id']} broadcast over named pipe")
        
        return True
    except Exception as e:
        print(f"IPC sending failed: {e}")
        return False
@app.route('/lab/upload', methods=['GET', 'POST'])
def upload_lab_report():
    """Upload new lab report and send to doctor"""
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            doctor_id = request.form.get('doctor_id')
            test_name = request.form.get('test_name')
            result = request.form.get('result')
            date = request.form.get('date')
            priority = request.form.get('priority', 'Normal')
            status = request.form.get('status', 'Pending')
            notes = request.form.get('notes', '')
            
            if not all([patient_id, doctor_id, test_name, result, date]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('lab_upload.html')
            
            labreport_path = os.path.join(BASE_DIR, 'labreport.csv')
            # Check if labreport.csv exists, else create empty dataframe
            if os.path.exists(labreport_path):
                lab_df = pd.read_csv(labreport_path)
            else:
                # Create empty DataFrame with columns
                lab_df = pd.DataFrame(columns=[
                    'doctor_id', 'patient_id', 'report_id', 'test_name', 'result',
                    'date', 'priority', 'status', 'notes', 'file_path', 'created_at'
                ])
            
            # Generate unique report ID
            report_id = f"R{1000 + len(lab_df) + 1}"
            
            # Handle file upload if provided
            file_path = None
            if 'lab_report' in request.files:
                file = request.files['lab_report']
                if file and file.filename:
                    # Create uploads directory if it doesn't exist
                    uploads_dir = os.path.join(BASE_DIR, 'static', 'uploads', 'lab_reports')
                    os.makedirs(uploads_dir, exist_ok=True)
                    
                    # Save file with report ID
                    file_extension = os.path.splitext(file.filename)[1]
                    filename = f"{report_id}{file_extension}"
                    file_path_save = os.path.join(uploads_dir, filename)
                    file.save(file_path_save)
                    
                    # Store relative path for database
                    file_path = f"uploads/lab_reports/{filename}"
            
            # Ensure file_path column exists
            if 'file_path' not in lab_df.columns:
                lab_df['file_path'] = None
            
            new_report = {
                'doctor_id': doctor_id,
                'patient_id': patient_id,
                'report_id': report_id,
                'test_name': test_name,
                'result': result,
                'date': date,
                'priority': priority,
                'status': status,
                'notes': notes,
                'file_path': file_path,
                'created_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            lab_df = pd.concat([lab_df, pd.DataFrame([new_report])], ignore_index=True)
            safe_save_csv(lab_df, labreport_path)
            
            ipc_message = {
                'type': 'lab_report',
                'timestamp': pd.Timestamp.now().isoformat(),
                'patient_id': patient_id,
                'doctor_id': doctor_id,
                'report_id': report_id,
                'test_name': test_name,
                'result': result,
                'date': date,
                'priority': priority,
                'status': status
            }
            
            send_lab_report_ipc(ipc_message)
            
            flash(f'Lab report uploaded and sent to doctor successfully! Report ID: {report_id}', 'success')
            return redirect(url_for('upload_lab_report'))
            
        except Exception as e:
            flash(f'Error uploading lab report: {str(e)}', 'danger')
            return render_template('lab_upload.html')
    
    # Handle missing CSV files gracefully
    try:
        patients_path = os.path.join(BASE_DIR, 'patients.csv')
        if os.path.exists(patients_path):
            patients_df = pd.read_csv(patients_path)
            patients = patients_df[['patient_id', 'first_name', 'last_name']].to_dict(orient='records') if not patients_df.empty else []
        else:
            patients = []
    except Exception as e:
        print(f"Error loading patients: {e}")
        patients = []
    
    try:
        if os.path.exists(doctors_path):
            doctors_df = pd.read_csv(doctors_path)
            doctors = doctors_df[['doctor_id', 'first_name', 'last_name', 'specialization']].to_dict(orient='records') if not doctors_df.empty else []
        else:
            doctors = []
    except Exception as e:
        print(f"Error loading doctors: {e}")
        doctors = []
    
    return render_template('lab_upload.html', patients=patients, doctors=doctors)


@app.route('/lab/generate_sample', methods=['POST'])
def generate_sample_lab_records():
    """Generate sample lab records for testing"""
    try:
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        doctors_df = pd.read_csv(doctors_path)
        labreport_path = os.path.join(BASE_DIR, 'labreport.csv')
        if os.path.exists(labreport_path):
            lab_df = pd.read_csv(labreport_path)
        else:
            lab_df = pd.DataFrame(columns=[
                'doctor_id', 'patient_id', 'report_id', 'test_name', 'result',
                'date', 'priority', 'status', 'notes', 'created_at'
            ])

        lab_tests = [
            {'name': 'Complete Blood Count', 'normal_range': 'Normal', 'abnormal': 'Low Hemoglobin'},
            {'name': 'Lipid Panel', 'normal_range': 'Normal', 'abnormal': 'High LDL Cholesterol'},
            {'name': 'Blood Sugar', 'normal_range': '70-100 mg/dL', 'abnormal': 'Fasting 150 mg/dL'},
            {'name': 'Chest X-Ray', 'normal_range': 'Clear', 'abnormal': 'Pneumonia detected'},
            {'name': 'ECG', 'normal_range': 'Normal rhythm', 'abnormal': 'Irregular heartbeat'},
            {'name': 'Urine Analysis', 'normal_range': 'Normal', 'abnormal': 'Protein in urine'},
            {'name': 'Liver Function Test', 'normal_range': 'Normal', 'abnormal': 'Elevated ALT'},
            {'name': 'Kidney Function Test', 'normal_range': 'Normal', 'abnormal': 'High Creatinine'},
            {'name': 'Thyroid Function Test', 'normal_range': 'Normal', 'abnormal': 'Hypothyroidism'},
            {'name': 'Vitamin D', 'normal_range': '30-100 ng/mL', 'abnormal': 'Deficient 15 ng/mL'}
        ]
        
        new_reports = []
        import random
        for i in range(20):
            patient = patients_df.sample(1).iloc[0]
            doctor = doctors_df.sample(1).iloc[0]
            test = lab_tests[i % len(lab_tests)]
            
            is_abnormal = random.random() < 0.3
            result = test['abnormal'] if is_abnormal else test['normal_range']
            priority = 'Critical' if is_abnormal and random.random() < 0.5 else 'Normal'
            
            days_ago = random.randint(1, 30)
            test_date = (pd.Timestamp.now() - pd.Timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            new_report = {
                'doctor_id': doctor['doctor_id'],
                'patient_id': patient['patient_id'],
                'report_id': f"R{1000 + len(lab_df) + 1 + i}",
                'test_name': test['name'],
                'result': result,
                'date': test_date,
                'priority': priority,
                'status': 'Completed',
                'notes': f'Sample lab report {i+1}',
                'created_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            new_reports.append(new_report)
        
        lab_df = pd.concat([lab_df, pd.DataFrame(new_reports)], ignore_index=True)
        safe_save_csv(lab_df, labreport_path)
        
        flash(f'Generated {len(new_reports)} sample lab records successfully!', 'success')
        return redirect(url_for('upload_lab_report'))
        
    except Exception as e:
        flash(f'Error generating sample records: {str(e)}', 'danger')
        return redirect(url_for('upload_lab_report'))

@app.route('/lab/reports')
def view_lab_reports():
    """View all lab reports with filtering"""
    try:
        labreport_path = os.path.join(BASE_DIR, 'labreport.csv')
        
        # Handle missing labreport.csv file
        if not os.path.exists(labreport_path):
            return render_template('lab_reports.html',
                                   reports=[],
                                   patients=[],
                                   doctors=[],
                                   current_filters={
                                       'patient_id': '',
                                       'doctor_id': '',
                                       'priority': '',
                                       'status': ''
                                   })
        
        lab_df = pd.read_csv(labreport_path)
        
        # Handle empty dataframe
        if lab_df.empty:
            patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv')) if os.path.exists(os.path.join(BASE_DIR, 'patients.csv')) else pd.DataFrame()
            doctors_df = pd.read_csv(doctors_path) if os.path.exists(doctors_path) else pd.DataFrame()
            
            patients = patients_df[['patient_id', 'first_name', 'last_name']].to_dict(orient='records') if not patients_df.empty else []
            doctors = doctors_df[['doctor_id', 'first_name', 'last_name']].to_dict(orient='records') if not doctors_df.empty else []
            
            return render_template('lab_reports.html',
                                   reports=[],
                                   patients=patients,
                                   doctors=doctors,
                                   current_filters={
                                       'patient_id': '',
                                       'doctor_id': '',
                                       'priority': '',
                                       'status': ''
                                   })
        
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        doctors_df = pd.read_csv(doctors_path)

        reports_with_details = lab_df.merge(
            patients_df[['patient_id', 'first_name', 'last_name', 'date_of_birth']],
            on='patient_id',
            how='left'
        ).merge(
            doctors_df[['doctor_id', 'first_name', 'last_name', 'specialization']],
            on='doctor_id',
            how='left'
        )
        
        patient_filter = request.args.get('patient_id', '')
        doctor_filter = request.args.get('doctor_id', '')
        priority_filter = request.args.get('priority', '')
        status_filter = request.args.get('status', '')
        
        if patient_filter:
            reports_with_details = reports_with_details[reports_with_details['patient_id'] == patient_filter]
        if doctor_filter:
            reports_with_details = reports_with_details[reports_with_details['doctor_id'] == doctor_filter]
        if priority_filter:
            reports_with_details = reports_with_details[reports_with_details['priority'] == priority_filter]
        if status_filter:
            reports_with_details = reports_with_details[reports_with_details['status'] == status_filter]
        
        # Handle date column - try different possible column names
        date_col = 'date' if 'date' in reports_with_details.columns else ('test_date' if 'test_date' in reports_with_details.columns else reports_with_details.columns[0] if len(reports_with_details.columns) > 0 else None)
        if date_col:
            reports_with_details = reports_with_details.sort_values(date_col, ascending=False)
        
        patients = patients_df[['patient_id', 'first_name', 'last_name']].to_dict(orient='records')
        doctors = doctors_df[['doctor_id', 'first_name', 'last_name']].to_dict(orient='records')
        
        return render_template('lab_reports.html',
                               reports=reports_with_details.to_dict(orient='records'),
                               patients=patients,
                               doctors=doctors,
                               current_filters={
                                   'patient_id': patient_filter,
                                   'doctor_id': doctor_filter,
                                   'priority': priority_filter,
                                   'status': status_filter
                               })
    except Exception as e:
        print(f"Error in view_lab_reports: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading lab reports: {str(e)}', 'danger')
        # Return empty template instead of redirecting
        return render_template('lab_reports.html',
                               reports=[],
                               patients=[],
                               doctors=[],
                               current_filters={
                                   'patient_id': '',
                                   'doctor_id': '',
                                   'priority': '',
                                   'status': ''
                               })

@app.route('/doctor/<doctor_id>/lab_notifications')
def doctor_lab_notifications(doctor_id):
    """Show lab notifications for doctor"""
    # Get notifications
    notifications = get_notifications('doctor', doctor_id, unread_only=False)
    
    # Get lab reports
    lab_df = pd.read_csv(os.path.join(BASE_DIR, 'labreport.csv'))
    doctor_reports = lab_df[lab_df['doctor_id'].astype(str) == str(doctor_id)]
    
    patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
    reports_with_patients = doctor_reports.merge(
        patients_df[['patient_id', 'first_name', 'last_name', 'date_of_birth']],
        on='patient_id',
        how='left'
    )
    
    # Merge notifications with reports
    for notification in notifications:
        if notification.get('report_id'):
            report = reports_with_patients[reports_with_patients['report_id'] == notification['report_id']]
            if not report.empty:
                notification['report_data'] = report.iloc[0].to_dict()
    
    return render_template('doctor_lab_notifications.html', 
                           reports=reports_with_patients.to_dict(orient='records'),
                           notifications=notifications,
                           doctor_id=doctor_id)


@app.route('/notification/<notification_id>/read', methods=['POST'])
def mark_notification_read_route(notification_id):
    """Mark a notification as read"""
    if mark_notification_read(notification_id):
        return {'success': True, 'message': 'Notification marked as read'}
    return {'success': False, 'message': 'Failed to mark notification as read'}, 400

@app.route('/report/<report_id>/view')
def view_report(report_id):
    """View full report details - marks notification as read"""
    try:
        lab_df = pd.read_csv(os.path.join(BASE_DIR, 'labreport.csv'))
        report = lab_df[lab_df['report_id'] == report_id]
        
        if report.empty:
            flash('Report not found', 'danger')
            return redirect(url_for('index'))
        
        report_data = report.iloc[0].to_dict()
        
        # Get patient and doctor info
        patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
        doctors_df = pd.read_csv(doctors_path)
        
        patient = patients_df[patients_df['patient_id'].astype(str) == str(report_data['patient_id'])]
        doctor = doctors_df[doctors_df['doctor_id'].astype(str) == str(report_data['doctor_id'])]
        
        patient_info = patient.iloc[0].to_dict() if not patient.empty else {}
        doctor_info = doctor.iloc[0].to_dict() if not doctor.empty else {}
        
        # Mark all notifications for this report as read
        notifications_path = os.path.join(BASE_DIR, 'notifications.csv')
        if os.path.exists(notifications_path):
            try:
                notifications_df = pd.read_csv(notifications_path)
                notifications_df.loc[
                    notifications_df['report_id'].astype(str) == str(report_id),
                    'is_read'
                ] = True
                safe_save_csv(notifications_df, notifications_path)
            except Exception as e:
                print(f"Error marking notifications as read: {e}")
        
        return render_template('view_report.html',
                             report=report_data,
                             patient_info=patient_info,
                             doctor_info=doctor_info)
    except Exception as e:
        flash(f'Error loading report: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login with proper POST handling"""
    # Handle auto-login via query parameter
    if request.args.get('auto') == 'login':
        if not is_admin_authenticated():
            session['admin_logged_in'] = True
            session['admin_email'] = ADMIN_EMAIL
            session['is_admin'] = True
            session.permanent = True
        return redirect(url_for('admin_dashboard'))
    
    # Handle POST requests (form submission)
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        redirect_target = request.form.get('next') or request.args.get('next') or url_for('admin_dashboard')
        
        # Normalize email (lowercase, remove all whitespace)
        email_normalized = email.lower().strip().replace(' ', '').replace('\t', '').replace('\n', '')
        password_normalized = password.strip()
        
        # Expected values (normalized)
        expected_email = ADMIN_EMAIL.lower().strip().replace(' ', '')
        expected_password = ADMIN_PASSWORD.strip()
        
        # Debug logging
        print(f"\n{'='*50}")
        print(f"[ADMIN LOGIN] Login Attempt")
        print(f"  Received Email (raw): '{email}'")
        print(f"  Received Email (normalized): '{email_normalized}'")
        print(f"  Received Password (length): {len(password_normalized)}")
        print(f"  Expected Email: '{expected_email}'")
        print(f"  Expected Password: '{expected_password}' (length: {len(expected_password)})")
        print(f"{'='*50}\n")
        
        # Check credentials - exact match after normalization
        email_ok = email_normalized == expected_email
        password_ok = password_normalized == expected_password
        
        print(f"  Email Match: {email_ok} (normalized: '{email_normalized}' == '{expected_email}')")
        print(f"  Password Match: {password_ok} (normalized: '{password_normalized}' == '{expected_password}')")
        
        if email_ok and password_ok:
            # Set session with all required flags
            session['admin_logged_in'] = True
            session['admin_email'] = ADMIN_EMAIL
            session['is_admin'] = True
            session.permanent = True
            
            # Force session save
            try:
                session.modified = True
            except:
                pass
            
            flash('Welcome back, Administrator!', 'success')
            print(f"[ADMIN LOGIN] ✅ SUCCESS - Session set, redirecting...")
            print(f"  Session admin_logged_in: {session.get('admin_logged_in')}")
            print(f"  Session admin_email: {session.get('admin_email')}")
            print(f"  Session is_admin: {session.get('is_admin')}")
            print(f"  Redirecting to: {redirect_target}")
            print(f"{'='*50}\n")
            
            # Use redirect with _external to ensure proper URL
            return redirect(redirect_target)
        else:
            error_details = []
            if not email_ok:
                error_details.append(f"Email mismatch: received '{email_normalized}', expected '{expected_email}'")
            if not password_ok:
                error_details.append(f"Password mismatch: received length {len(password_normalized)}, expected length {len(expected_password)}")
            
            # More user-friendly error message
            if not email_ok and not password_ok:
                error_msg = 'Invalid email and password. Please check both fields.'
            elif not email_ok:
                error_msg = f'Invalid email address. Expected: {ADMIN_EMAIL}'
            else:
                error_msg = 'Invalid password. Please try again.'
            
            flash(error_msg, 'danger')
            print(f"[ADMIN LOGIN] ❌ FAILED - {error_msg}")
            print(f"  Details: {' | '.join(error_details)}")
            print(f"{'='*50}\n")
    
    # Handle GET requests - show login form
    next_url = request.args.get('next') or url_for('admin_dashboard')
    return render_template('admin_login.html', next_url=next_url, default_email=ADMIN_EMAIL)


@app.route('/admin/logout')
def admin_logout():
    """Clear admin session."""
    session.pop('admin_logged_in', None)
    session.pop('admin_email', None)
    flash('You have been signed out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/call_next', methods=['POST'])
def admin_call_next():
    """Advance queue and mark the next appointment as in-session."""
    gate = require_admin()
    if gate:
        return gate
    
    queues, *_ = build_two_queue_context()
    next_appointment_id = select_next_patient(queues)
    
    if not next_appointment_id:
        flash('No scheduled patients are waiting in the queue.', 'info')
        return redirect(url_for('admin_dashboard'))
    
    try:
        with appointment_guard(next_appointment_id, context_label="admin-call-next"):
            appointments_df = pd.read_csv(appointments_path)
            mask = appointments_df['appointment_id'].astype(str) == str(next_appointment_id)
            if not mask.any():
                flash('Selected appointment could not be found.', 'danger')
                return redirect(url_for('admin_dashboard'))
            
            patient_id = appointments_df.loc[mask, 'patient_id'].iloc[0]
            previous_status = appointments_df.loc[mask, 'status'].iloc[0]
            appointments_df.loc[mask, 'status'] = 'in-session'
            safe_save_csv(appointments_df, appointments_path)
            
            publish_ipc_event('admin.call_next', {
                'appointment_id': next_appointment_id,
                'patient_id': patient_id,
                'previous_status': previous_status
            })
        
        flash(f'Patient {patient_id} (Appointment {next_appointment_id}) is now in-session.', 'success')
    except Exception as exc:
        flash(f'Failed to call next patient: {exc}', 'danger')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/update_payment_status', methods=['POST'])
def admin_update_payment_status():
    gate = require_admin()
    if gate:
        return gate
    """Admin route to update payment status from Pending to Completed"""
    bill_id = request.form.get('bill_id')
    new_status = request.form.get('status', 'Completed')
    
    if not bill_id:
        flash('Bill ID is required', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    billing_path = os.path.join(BASE_DIR, 'billing.csv')
    if os.path.exists(billing_path):
        try:
            billing_df = pd.read_csv(billing_path)
            mask = billing_df['bill_id'].astype(str) == str(bill_id)
            if mask.any():
                billing_df.loc[mask, 'payment_status'] = new_status
                safe_save_csv(billing_df, billing_path)
                flash(f'Payment status updated to {new_status} for Bill {bill_id}', 'success')
            else:
                flash('Bill not found', 'danger')
        except Exception as e:
            flash(f'Error updating payment status: {str(e)}', 'danger')
    else:
        flash('Billing system not available', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard route - with simplified access"""
    # Simplified authentication - always allow access for demo/testing
    # Set session if not already set
    if not is_admin_authenticated():
        session['admin_logged_in'] = True
        session['admin_email'] = ADMIN_EMAIL
        session['is_admin'] = True
        session.permanent = True
        flash('Welcome to Admin Dashboard!', 'success')
    
    queues, total_patients, active_consultations, severity_counts = build_two_queue_context()
    mutex_snapshot = get_mutex_snapshot()
    
    # Get all pending bills
    pending_bills = []
    billing_path = os.path.join(BASE_DIR, 'billing.csv')
    if os.path.exists(billing_path):
        try:
            billing_df = pd.read_csv(billing_path)
            pending_bills = billing_df[billing_df['payment_status'].str.lower() == 'pending'].to_dict(orient='records')
        except Exception as e:
            print(f"Error loading billing data: {e}")
    
    # Doctor directory & analytics
    doctor_list = []
    doctor_summary = {
        'total': 0,
        'avg_experience': 0,
        'by_specialization': {},
        'by_branch': {}
    }
    if os.path.exists(doctors_path):
        try:
            doctors_df = pd.read_csv(doctors_path)
            if not doctors_df.empty:
                doctors_df = doctors_df.fillna('')
                doctor_list = doctors_df[['doctor_id', 'first_name', 'last_name', 'specialization',
                                          'hospital_branch', 'phone_number', 'email', 'years_experience']].to_dict(orient='records')
                doctor_summary['total'] = len(doctors_df)
                if doctors_df['years_experience'].notna().any():
                    doctor_summary['avg_experience'] = round(doctors_df['years_experience'].dropna().astype(float).mean(), 1)
                doctor_summary['by_specialization'] = doctors_df['specialization'].value_counts().to_dict()
                doctor_summary['by_branch'] = doctors_df['hospital_branch'].value_counts().to_dict()
        except Exception as e:
            print(f"Error loading doctor directory: {e}")
    
    lookup_endpoint = 'lookup_patient' if 'lookup_patient' in app.view_functions else 'index'
    quick_links = {
        'lookup': url_for(lookup_endpoint)
    }
    
    return render_template(
        'admin_dashboard.html',
        queues=queues,
        total_patients=total_patients,
        active_consultations=active_consultations,
        severity_counts=severity_counts,
        pending_bills=pending_bills,
        doctor_list=doctor_list,
        doctor_summary=doctor_summary,
        quick_links=quick_links,
        mutex_snapshot=mutex_snapshot
    )

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    """Patient login with OTP"""
    # Handle pre-filled patient_id from query params
    patient_id_param = request.args.get('patient_id', '')
    
    if request.method == 'POST':
        step = request.form.get('step', 'init')
        
        if step == 'init':
            # Step 1: Get patient ID and mobile
            patient_id = request.form.get('patient_id', '').strip()
            mobile = request.form.get('mobile', '').strip()
            
            if not patient_id:
                flash('Please enter your Patient ID', 'danger')
                return render_template('patient_login.html', step=1)
            
            # Verify patient exists
            patients_df = pd.read_csv(os.path.join(BASE_DIR, 'patients.csv'))
            patient = patients_df[patients_df['patient_id'].astype(str) == str(patient_id)]
            
            if patient.empty:
                flash('Patient ID not found', 'danger')
                return render_template('patient_login.html', step=1)
            
            patient_data = patient.iloc[0].to_dict()
            
            # If mobile provided, verify it matches
            if mobile and str(patient_data.get('contact_number', '')) != str(mobile):
                flash('Mobile number does not match patient record', 'danger')
                return render_template('patient_login.html', step=1, patient_id=patient_id)
            
            # Generate and send OTP
            otp = generate_otp()
            patient_mobile = str(patient_data.get('contact_number', ''))
            
            session['login_patient_id'] = patient_id
            session['login_otp'] = otp
            session['login_mobile'] = patient_mobile
            
            # Send OTP
            send_otp_sms(otp, patient_mobile)
            
            flash('OTP sent to your registered mobile number', 'success')
            return render_template('patient_login.html', step=2, patient_id=patient_id, debug_otp=otp)
        
        elif step == 'verify':
            # Step 2: Verify OTP
            otp = request.form.get('otp', '').strip()
            patient_id = session.get('login_patient_id')
            
            if not patient_id or 'login_otp' not in session:
                flash('Session expired. Please login again', 'danger')
                return redirect(url_for('patient_login'))
            
            if otp != session.get('login_otp'):
                flash('Incorrect OTP. Please try again', 'danger')
                return render_template('patient_login.html', step=2, patient_id=patient_id, debug_otp=session.get('login_otp'))
            
            # OTP verified - redirect to dashboard
            session.pop('login_otp', None)
            session.pop('login_mobile', None)
            flash('Login successful!', 'success')
            return redirect(url_for('patient_dashboard', patient_id=patient_id))
    
    return render_template('patient_login.html', step=1, patient_id=patient_id_param)

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    """Doctor login with password"""
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id', '').strip()
        password = request.form.get('password', '').strip()
        
        if not doctor_id or not password:
            flash('Please enter both Doctor ID and Password', 'danger')
            return render_template('doctor_login.html')
        
        # Verify doctor exists
        doctors_df = pd.read_csv(doctors_path)
        doctor = doctors_df[doctors_df['doctor_id'].astype(str) == str(doctor_id)]
        
        if doctor.empty:
            flash('Doctor ID not found', 'danger')
            return render_template('doctor_login.html')
        
        import hashlib
        
        # Ensure password column exists
        if 'password' not in doctors_df.columns:
            doctors_df['password'] = ''
        
        # Get stored password (may be empty)
        doctor_index = doctors_df[doctors_df['doctor_id'].astype(str) == str(doctor_id)].index[0]
        stored_password = str(doctors_df.loc[doctor_index, 'password']).strip() if pd.notna(doctors_df.loc[doctor_index, 'password']) else ''
        
        # Calculate default password hash: {doctor_id}123
        default_password_hash = hashlib.md5(f"{doctor_id}123".encode()).hexdigest()
        
        # If no password is stored, use default and save it
        if not stored_password:
            doctors_df.loc[doctor_index, 'password'] = default_password_hash
            safe_save_csv(doctors_df, doctors_path)
            stored_password = default_password_hash
            flash('Default password set. Please change it after login.', 'info')
        
        # Hash the provided password
        password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # Compare hashes
        if password_hash != stored_password:
            # Also check if they entered the plain default password (for convenience)
            if password == f"{doctor_id}123":
                # They entered the plain default password, update stored hash
                doctors_df.loc[doctor_index, 'password'] = default_password_hash
                safe_save_csv(doctors_df, doctors_path)
                flash('Login successful! (Default password accepted)', 'success')
                return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
            else:
                flash(f'Incorrect password. Default password is: {doctor_id}123', 'danger')
                return render_template('doctor_login.html', doctor_id=doctor_id)
        
        # Login successful
        flash('Login successful!', 'success')
        return redirect(url_for('doctor_dashboard', doctor_id=doctor_id))
    
    return render_template('doctor_login.html')

@app.after_request
def add_header(response):
    """Force browser to always reload fresh data."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    # Run on all interfaces (0.0.0.0) to allow access from other devices on the network
    # Change to host='127.0.0.1' if you only want local access
    app.run(debug=True, host='0.0.0.0', port=5000)
