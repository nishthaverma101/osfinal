# Mutex Demonstration Guide

## What is Mutex?

A **Mutex (Mutual Exclusion)** is an operating system concept that ensures only one process/thread can access a shared resource at a time. In this hospital management system, mutexes prevent race conditions when multiple doctors try to update the same appointment simultaneously.

## How Mutex Works in This Project

The system uses **scoped locks** that protect individual appointments. When a doctor clicks "Start Consultation" or "Complete Consultation", the system:

1. **Acquires a lock** on that specific appointment ID
2. **Performs the update** (changes status from "Scheduled" → "in-session" → "completed")
3. **Releases the lock** so other operations can proceed

If two doctors try to update the same appointment at the same time, the second request waits until the first completes.

## How to Demonstrate Mutex Functionality

### Method 1: Using Multiple Browser Tabs/Windows (Recommended)

1. **Start the Flask application:**
   ```bash
   python app.py
   ```

2. **Open two browser windows/tabs** and log in as different doctors:
   - Window 1: Login as `D001` (password: `D001123`)
   - Window 2: Login as `D002` (password: `D002123`)

3. **Find a patient with status "Scheduled"** in both dashboards (same patient ID)

4. **Simultaneously click "Start"** on the same appointment in both windows:
   - Click "Start" in Window 1
   - **Immediately** (within 1-2 seconds) click "Start" in Window 2

5. **Observe the behavior:**
   - **Window 1**: Should immediately update to "in-session"
   - **Window 2**: Will either:
     - Show an error/flash message
     - Wait briefly then update (if the first request completes quickly)
     - Show the appointment is already "in-session"

6. **Check the server console** - You should see mutex log messages:
   ```
   ============ [MUTEX 🔒] Waiting for lock [A001] (context: /start_consultation) ============
   ============ [MUTEX ✅] Lock acquired [A001] (context: /start_consultation) ============
   ============ [MUTEX 🔓] Lock released [A001] (context: /start_consultation) ============
   ```

7. **Check the Mutex Monitor** on the doctor dashboard - it shows active locks in real-time

### Method 2: Using Browser Developer Tools (Network Tab)

1. **Open browser DevTools** (F12) → Network tab
2. **Log in as a doctor** and find a scheduled appointment
3. **Right-click "Start" button** → Inspect
4. **Note the form action URL** (e.g., `/start_consultation`)
5. **Open a second tab** and log in as another doctor
6. **In DevTools Console**, run:
   ```javascript
   // Simulate rapid concurrent requests
   fetch('/start_consultation', {
     method: 'POST',
     headers: {'Content-Type': 'application/x-www-form-urlencoded'},
     body: 'appointment_id=A001&doctor_id=D001'
   });
   fetch('/start_consultation', {
     method: 'POST',
     headers: {'Content-Type': 'application/x-www-form-urlencoded'},
     body: 'appointment_id=A001&doctor_id=D002'
   });
   ```
7. **Watch the Network tab** - one request will complete first, the second will wait

### Method 3: Using Python Script (Advanced)

Create a test script `test_mutex.py`:

```python
import requests
import threading
import time

BASE_URL = "http://localhost:5000"

def start_consultation(appointment_id, doctor_id, thread_name):
    print(f"[{thread_name}] Attempting to start consultation {appointment_id}...")
    response = requests.post(
        f"{BASE_URL}/start_consultation",
        data={
            'appointment_id': appointment_id,
            'doctor_id': doctor_id
        }
    )
    print(f"[{thread_name}] Response: {response.status_code} - {response.url}")

# Simulate two doctors trying to start the same consultation
appointment_id = "A001"
thread1 = threading.Thread(
    target=start_consultation,
    args=(appointment_id, "D001", "Doctor-1")
)
thread2 = threading.Thread(
    target=start_consultation,
    args=(appointment_id, "D002", "Doctor-2")
)

thread1.start()
time.sleep(0.1)  # Small delay to ensure both try simultaneously
thread2.start()

thread1.join()
thread2.join()
```

Run it: `python test_mutex.py`

## What to Look For

### ✅ Success Indicators:

1. **Server Console Logs:**
   - `[MUTEX 🔒] Waiting for lock` - Shows lock acquisition attempt
   - `[MUTEX ✅] Lock acquired` - Shows successful lock
   - `[MUTEX 🔓] Lock released` - Shows lock release

2. **Doctor Dashboard Mutex Monitor:**
   - Shows active locks with appointment ID, context, and timestamp
   - Updates in real-time as locks are acquired/released

3. **No Data Corruption:**
   - Appointment status changes correctly
   - No duplicate updates
   - CSV files remain consistent

### ❌ Without Mutex (What Would Happen):

- Both requests might update the same appointment
- Status could be inconsistent
- CSV file could get corrupted
- Race conditions could cause data loss

## Key Files to Understand

1. **`app.py`** (lines 42-112):
   - `ScopedLockRegistry` class - manages locks per appointment
   - `appointment_guard()` context manager - acquires/releases locks
   - `_highlight_log()` - logs mutex activity

2. **`lock_utils.py`**:
   - `CrossProcessFileLock` - file-level locking for CSV writes
   - Prevents multiple processes from writing simultaneously

3. **`doctor_dashboard.html`** (lines 334-376):
   - Mutex Monitor section - displays active locks

## Tips for Best Demonstration

1. **Use appointments with status "Scheduled"** - they're most likely to have concurrent access
2. **Time your clicks carefully** - click within 1-2 seconds of each other
3. **Watch the server console** - it shows the most detailed mutex activity
4. **Refresh dashboards** after testing to see final state
5. **Use different doctors** - ensures you're testing concurrent access properly

## Real-World Analogy

Think of a mutex like a **bathroom key**:
- Only one person can use the bathroom at a time
- Others must wait until the key is returned
- Prevents conflicts and ensures orderly access

In our system:
- The "bathroom" = appointment record
- The "key" = mutex lock
- "Using the bathroom" = updating appointment status

## Summary

Mutex ensures **thread-safe operations** in a multi-user environment. By demonstrating concurrent access attempts, you show how the operating system concept of mutual exclusion prevents data corruption and race conditions in a real-world hospital management system.

