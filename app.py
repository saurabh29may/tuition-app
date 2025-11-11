import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# -------------------------------
# Database setup
# -------------------------------
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('tuition.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    grade TEXT,
    monthly_fee INTEGER,
    start_date TEXT,
    contact TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    month TEXT,
    amount_paid INTEGER,
    payment_date TEXT,
    payment_mode TEXT,
    FOREIGN KEY(student_id) REFERENCES students(student_id)
)''')
conn.commit()

# -------------------------------
# App UI
# -------------------------------
st.set_page_config(page_title="Smart Tuition Fee Tracker", layout="wide")
st.title("🎓 Smart Tuition Fee Tracker")

menu = ["Dashboard", "Add Student", "Record Payment", "View Payments", "Payment Summary"]
choice = st.sidebar.selectbox("Menu", menu)

# -------------------------------
# Add Student
# -------------------------------
if choice == "Add Student":
    st.subheader("🧍 Add New Student")
    name = st.text_input("Student Name")
    grade = st.text_input("Grade / Class")
    monthly_fee = st.number_input("Monthly Fee (₹)", min_value=0)
    start_date = st.date_input("Start Date")
    contact = st.text_input("Contact Info (optional)")

    if st.button("Add Student"):
        if name and monthly_fee > 0:
            c.execute("INSERT INTO students (name, grade, monthly_fee, start_date, contact) VALUES (?, ?, ?, ?, ?)",
                      (name, grade, monthly_fee, start_date.strftime("%Y-%m-%d"), contact))
            conn.commit()
            st.success(f"✅ {name} added successfully!")
        else:
            st.warning("⚠️ Please fill all mandatory fields (name and fee).")

# -------------------------------
# Record Payment
# -------------------------------
elif choice == "Record Payment":
    st.subheader("💰 Record Monthly Payment")

    students = pd.read_sql_query("SELECT * FROM students", conn)
    if not students.empty:
        student_names = students['name'].tolist()
        selected_student = st.selectbox("Select Student", student_names)
        student_row = students[students['name'] == selected_student].iloc[0]

        # Auto-fill current month
        current_month = datetime.now().strftime("%b %Y")
        month = st.text_input("Month", value=current_month)

        amount = st.number_input("Amount Paid", min_value=0, value=int(student_row['monthly_fee']))
        payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer"])

        if st.button("Record Payment"):
            # Check for duplicate payment
            check_query = """
                SELECT * FROM payments
                WHERE student_id = ? AND month = ?
            """
            existing = pd.read_sql_query(check_query, conn, params=(student_row['student_id'], month))

            if not existing.empty:
                st.warning(f"⚠️ Payment for {selected_student} in {month} already exists.")
            else:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO payments (student_id, month, amount_paid, payment_date, payment_mode)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    student_row['student_id'],
                    month,
                    amount,
                    datetime.now().strftime("%Y-%m-%d"),
                    payment_mode
                ))
                conn.commit()
                st.success(f"✅ Payment of ₹{amount} for {selected_student} recorded for {month}!")
    else:
        st.warning("⚠️ No students found. Please add a student first.")

# -------------------------------
# Dashboard
# -------------------------------
elif choice == "Dashboard":
    st.subheader("📊 Dashboard")
    payments_df = pd.read_sql("SELECT * FROM payments", conn)
    students_df = pd.read_sql("SELECT * FROM students", conn)

    total_collected = payments_df['amount_paid'].sum() if not payments_df.empty else 0
    st.metric("Total Collected (All Time)", f"₹{total_collected}")

    if not students_df.empty:
        current_month = datetime.now().strftime("%b %Y")
        paid_students = payments_df[payments_df['month'] == current_month]['student_id'].unique().tolist()
        unpaid_students = students_df[~students_df['student_id'].isin(paid_students)]

        st.write(f"### 🧾 Unpaid Students for {current_month}")
        if unpaid_students.empty:
            st.success("🎉 All students have paid for this month!")
        else:
            st.dataframe(unpaid_students[['name', 'grade', 'contact']])
    else:
        st.info("No students yet. Please add students first.")

# -------------------------------
# View Payments
# -------------------------------
elif choice == "View Payments":
    st.subheader("📜 Payment Records")
    df = pd.read_sql('''
        SELECT s.name, p.month, p.amount_paid, p.payment_mode, p.payment_date
        FROM payments p
        JOIN students s ON p.student_id = s.student_id
        ORDER BY p.payment_date DESC
    ''', conn)

    if not df.empty:
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "payments.csv", "text/csv")
    else:
        st.info("No payments recorded yet.")

# -------------------------------
# Payment Summary (Per Student)
# -------------------------------
elif choice == "Payment Summary":
    st.subheader("📘 Payment Summary per Student")

    students_df = pd.read_sql_query("SELECT * FROM students", conn)
    payments_df = pd.read_sql_query("SELECT * FROM payments", conn)

    if not students_df.empty:
        student_names = students_df['name'].tolist()
        selected_student = st.selectbox("Select Student", student_names)

        student = students_df[students_df['name'] == selected_student].iloc[0]
        student_id = student['student_id']

        # Filter payments for this student
        student_payments = payments_df[payments_df['student_id'] == student_id].sort_values('month')

        st.write(f"### 💳 Payment History for {selected_student}")
        if not student_payments.empty:
            display_df = student_payments[['month', 'amount_paid', 'payment_mode', 'payment_date']]
            display_df.rename(columns={
                'month': 'Month',
                'amount_paid': 'Amount Paid (₹)',
                'payment_mode': 'Mode',
                'payment_date': 'Payment Date'
            }, inplace=True)
            st.dataframe(display_df)

            # Summary
            total_paid = student_payments['amount_paid'].sum()
            months_paid = len(student_payments)
            st.write(f"✅ **Total Paid:** ₹{total_paid}")
            st.write(f"🗓️ **Months Paid:** {months_paid}")

            # Calculate pending months
            start_date = datetime.strptime(student['start_date'], "%Y-%m-%d")
            current_date = datetime.now()
            total_months = (current_date.year - start_date.year) * 12 + (current_date.month - start_date.month + 1)
            pending_months = total_months - months_paid
            if pending_months > 0:
                st.warning(f"⚠️ **Pending Months:** {pending_months}")
            else:
                st.success("🎉 All payments are up to date!")
        else:
            st.warning(f"No payments recorded for {selected_student} yet.")
    else:
        st.info("No students found. Please add students first.")
