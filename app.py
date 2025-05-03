# -*- coding: utf-8 -*-
"""app.py

Ky'ra Internship Dashboard for Streamlit Cloud.
Consolidates authentication, database, dashboard, and report generation.
"""

import streamlit as st
import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
import tempfile
import base64
import hashlib
import random
import uuid

# --- Streamlit Config ---
st.set_page_config(page_title="Ky'ra Internship Dashboard", layout="wide", initial_sidebar_state="expanded")
sns.set_style("whitegrid")

# --- Configuration ---
DB_PATH = os.path.join("/tmp", "internship_tracking.db") if "STREAMLIT_CLOUD" in os.environ else os.path.join(os.getcwd(), "internship_tracking.db")

USERS = {
    "student@example.com": {"name": "Alice", "password": hashlib.sha256("student123".encode()).hexdigest(), "role": "Student"},
    "college@example.com": {"name": "Prof. Smith", "password": hashlib.sha256("college123".encode()).hexdigest(), "role": "College"},
    "msme@example.com": {"name": "MSME Corp", "password": hashlib.sha256("msme123".encode()).hexdigest(), "role": "MSME"},
    "mentor@example.com": {"name": "Dr. Jones", "password": hashlib.sha256("mentor123".encode()).hexdigest(), "role": "Mentor"},
    "gov@example.com": {"name": "Gov Official", "password": hashlib.sha256("gov123".encode()).hexdigest(), "role": "Government"}
}

GREETINGS = {
    "Student": "Welcome back, [Name]! You're doing great today! 🌟",
    "College": "Hello, [Name]! Ready to guide your students to success? 📚",
    "MSME": "Hi, [Name]! Let's grow your business with talent! 🚀",
    "Mentor": "Welcome, [Name]! Your mentorship makes a difference! 💡",
    "Government": "Greetings, [Name]! Driving impact for the nation! 🏛️"
}

MOTIVATIONAL_PROMPTS = {
    "no_progress": "You're just getting started! Log your first internship to kick off your journey! 🚀",
    "some_progress": "Great work! You've completed some internships – keep pushing forward! 💪",
    "high_progress": "Wow, you're a star! You've completed multiple internships – keep shining! 🌟"
}

# --- Authentication ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(email, password, role):
    user_data = USERS.get(email)
    if user_data and user_data["password"] == hash_password(password) and user_data["role"] == role:
        return {"email": email, "name": user_data["name"], "role": role}
    return None

# --- Database Operations ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

@st.cache_data
def initialize_database():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS internships (
                internship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                company_name TEXT NOT NULL,
                duration TEXT NOT NULL,
                feedback TEXT,
                msme_digitalized INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                rating INTEGER,
                comments TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        raise Exception(f"Database initialization error: {str(e)}")
    finally:
        cur.close()

def fetch_student_data(email):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id, name FROM students WHERE email = ?", (email,))
        student = cur.fetchone()
        if student:
            student_id, name = student
            cur.execute("SELECT company_name, duration, feedback, msme_digitalized FROM internships WHERE student_id = ?", (student_id,))
            internships = cur.fetchall()
            return {
                "student_id": student_id,
                "name": name,
                "internships": [{"company_name": i[0], "duration": i[1], "feedback": i[2], "msme_digitalized": i[3]} for i in internships]
            }
        return None
    except sqlite3.Error as e:
        raise Exception(f"Error fetching student data: {str(e)}")
    finally:
        cur.close()

def log_internship(email, company, duration, feedback, msme_digitalized):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM students WHERE email = ?", (email,))
        student = cur.fetchone()
        if not student:
            name = email.split("@")[0].capitalize()
            cur.execute("INSERT INTO students (name, email) VALUES (?, ?)", (name, email))
            conn.commit()
            cur.execute("SELECT student_id FROM students WHERE email = ?", (email,))
            student = cur.fetchone()
        student_id = student[0]
        cur.execute("""
            INSERT INTO internships (student_id, company_name, duration, feedback, msme_digitalized)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, company, duration, feedback, msme_digitalized))
        conn.commit()
        return True
    except sqlite3.Error as e:
        raise Exception(f"Error logging internship: {str(e)}")
    finally:
        cur.close()

def fetch_metrics():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM internships")
        total_internships = cur.fetchone()[0]
        cur.execute("SELECT SUM(msme_digitalized) FROM internships")
        total_msmes = cur.fetchone()[0] or 0
        certifications_issued = total_internships
        return {
            "total_internships": total_internships,
            "total_msmes": total_msmes,
            "certifications_issued": certifications_issued
        }
    except sqlite3.Error as e:
        raise Exception(f"Error fetching metrics: {str(e)}")
    finally:
        cur.close()

def fetch_reports():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.name, s.email, i.company_name, i.duration, i.feedback, i.msme_digitalized
            FROM students s
            LEFT JOIN internships i ON s.student_id = i.student_id
        """)
        rows = cur.fetchall()
        return [{"name": r[0], "email": r[1], "company_name": r[2], "duration": r[3], "feedback": r[4], "msme_digitalized": r[5]} for r in rows]
    except sqlite3.Error as e:
        raise Exception(f"Error fetching reports: {str(e)}")
    finally:
        cur.close()

def log_feedback(student_id, rating, comments):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO feedback (student_id, rating, comments) VALUES (?, ?, ?)", (student_id, rating, comments))
        conn.commit()
        return True
    except sqlite3.Error as e:
        raise Exception(f"Error logging feedback: {str(e)}")
    finally:
        cur.close()

# --- Report Generation ---
def generate_pdf_report(report_data):
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        c = canvas.Canvas(temp_file.name)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Ky'ra Internship Report")
        y = 700
        for entry in report_data:
            text = f"Name: {entry['name']}, Company: {entry['company_name'] or 'N/A'}, Duration: {entry['duration'] or 'N/A'}"
            c.drawString(100, y, text)
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        c.save()
        return temp_file.name
    except Exception as e:
        raise Exception(f"Error generating PDF: {str(e)}")

# --- Mock API Data ---
def fetch_api_metrics():
    return {
        "total_internships": random.randint(50, 100),
        "total_msmes": random.randint(20, 50),
        "certifications_issued": random.randint(50, 100)
    }

# --- Dashboard Rendering ---
def render_ticker():
    metrics = fetch_api_metrics()
    ticker_html = """
    <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>
        <marquee behavior='scroll' direction='left'>
            🌟 {internships} Internships Completed | 🚀 {msmes} MSMEs Supported | 📜 {certifications} Certifications Issued
        </marquee>
    </div>
    """.format(
        internships=metrics["total_internships"],
        msmes=metrics["total_msmes"],
        certifications=metrics["certifications_issued"]
    )
    st.markdown(ticker_html, unsafe_allow_html=True)

def display_motivational_prompt(user_data, role):
    if role == "Student":
        internships = len(user_data.get("internships", []))
        if internships >= 3:
            prompt = MOTIVATIONAL_PROMPTS["high_progress"]
        elif internships > 0:
            prompt = MOTIVATIONAL_PROMPTS["some_progress"]
        else:
            prompt = MOTIVATIONAL_PROMPTS["no_progress"]
        st.info(prompt)

def render_student_dashboard(user):
    email = user["email"]
    student_data = fetch_student_data(email)
    
    if student_data:
        display_motivational_prompt(student_data, "Student")
        total_internships = len(student_data["internships"])
        st.sidebar.success(
            f"Hi {student_data['name']}! You've logged {total_internships} internship{'s' if total_internships > 1 else ''}! 🚀"
        )

    st.sidebar.header("Your Journey")
    menu = ["Your Progress", "Log Internship", "Opportunities", "Feedback", "Generate Report"]
    choice = st.sidebar.selectbox("Navigate", menu)

    metrics = fetch_metrics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Internships Completed", metrics.get("total_internships", 0))
    with col2:
        st.metric("MSMEs Supported", metrics.get("total_msmes", 0))
    with col3:
        st.metric("Certifications Issued", metrics.get("certifications_issued", 0))

    if choice == "Your Progress":
        st.header("📈 Your Progress")
        if student_data and student_data["internships"]:
            df = pd.DataFrame(student_data["internships"])
            st.dataframe(df)
            fig, ax = plt.subplots()
            sns.countplot(x="msme_digitalized", data=df, ax=ax)
            st.pyplot(fig)
        else:
            st.info("No internships logged yet. Start by logging one! 😊")

    elif choice == "Log Internship":
        st.header("🛠️ Log Internship")
        with st.form("internship_form"):
            company = st.text_input("Company Name")
            duration = st.text_input("Duration (e.g., 3 months)")
            feedback = st.text_area("Feedback")
            msme_digitalized = st.number_input("MSMEs Digitalized", min_value=0)
            submit = st.form_submit_button("Submit Internship")
            if submit:
                if company and duration:
                    with st.spinner("Saving your internship..."):
                        try:
                            success = log_internship(email, company, duration, feedback, msme_digitalized)
                            if success:
                                st.success("Internship logged successfully! 🎉")
                                st.balloons()
                            else:
                                st.error("Failed to log internship.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                else:
                    st.error("Please fill in all required fields.")

    elif choice == "Opportunities":
        st.header("🚀 Opportunities")
        st.info("Explore new internship opportunities soon! Keep checking back! 😊")

    elif choice == "Feedback":
        st.header("🗣️ Share Your Feedback")
        if student_data:
            feedback_type = st.radio("Choose feedback method:", ["Star Rating", "Emoji Scale"])
            with st.form("feedback_form"):
                if feedback_type == "Star Rating":
                    rating = st.slider("Rate your experience", 1, 5, 3)
                    comments = st.text_area("Comments")
                else:
                    emoji_ratings = {"😊": 5, "🙂": 3, "😔": 1}
                    emoji = st.selectbox("How do you feel?", list(emoji_ratings.keys()))
                    rating = emoji_ratings[emoji]
                    comments = st.text_area("Comments (optional)")
                submit = st.form_submit_button("Submit Feedback")
                if submit:
                    with st.spinner("Submitting feedback..."):
                        try:
                            if log_feedback(student_data["student_id"], rating, comments):
                                st.success("Thanks for your feedback! You're amazing! 🌟")
                            else:
                                st.error("Failed to submit feedback.")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

    elif choice == "Generate Report":
        st.header("📄 Generate Report")
        with st.spinner("Generating your internship report..."):
            try:
                report_data = fetch_reports()
                if report_data:
                    pdf_path = generate_pdf_report(report_data)
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    b64_pdf = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="internship_report.pdf">📥 Download Report</a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.info("No report data available yet.")
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")

def render_college_mentor_dashboard():
    st.header("📊 College/Mentor Dashboard")
    metrics = fetch_metrics()
    st.write("### Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Internships", metrics.get("total_internships", 0))
    with col2:
        st.metric("MSMEs Supported", metrics.get("total_msmes", 0))
    with col3:
        st.metric("Certifications Issued", metrics.get("certifications_issued", 0))
    st.write("### Reports")
    report_data = fetch_reports()
    if report_data:
        df = pd.DataFrame(report_data)
        st.dataframe(df)

def render_msme_dashboard():
    st.header("🏢 MSME Dashboard")
    st.info("View your digitalization progress and student contributions soon! 😊")

def render_government_dashboard():
    st.header("🏛️ Government Dashboard")
    metrics = fetch_metrics()
    st.write("### Program Impact")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Internships", metrics.get("total_internships", 0))
    with col2:
        st.metric("MSMEs Supported", metrics.get("total_msmes", 0))
    with col3:
        st.metric("Certifications Issued", metrics.get("certifications_issued", 0))

def render_dashboard(user, role):
    render_ticker()
    if role == "Student":
        render_student_dashboard(user)
    elif role in ["College", "Mentor"]:
        render_college_mentor_dashboard()
    elif role == "MSME":
        render_msme_dashboard()
    elif role == "Government":
        render_government_dashboard()

# --- Main Application ---
def main():
    st.title("🌟 Ky'ra: Your Internship Journey Mentor")
    initialize_database()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.role = None

    if not st.session_state.authenticated:
        st.header("Welcome to Ky'ra! 🎉")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Student", "College", "MSME", "Mentor", "Government"])
        if st.button("Login"):
            with st.spinner("Authenticating..."):
                try:
                    user = authenticate_user(email, password, role)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.role = role
                        st.success(f"Welcome, {user['name']}! You're ready to shine! ✨")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
                except Exception as e:
                    st.error(f"Authentication error: {str(e)}")
    else:
        user_name = st.session_state.user["name"]
        role = st.session_state.role
        greeting = GREETINGS.get(role, "Welcome back!").replace('[Name]', user_name)
        st.markdown(f"### {greeting}")
        try:
            render_dashboard(st.session_state.user, st.session_state.role)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()