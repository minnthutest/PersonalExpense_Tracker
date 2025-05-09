import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px
import kaleido  # Ensure kaleido is installed: pip install -U kaleido

from logic.expense_manager import *
from database.database import create_user_table, create_expense_table, delete_user, reset_password  # Assuming you import reset_password

# Init DB
create_user_table()
create_expense_table()

# Session setup
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# Load CSS
def load_css():
    try:
        with open("css/style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Styling will be minimal.")

load_css()

# Authentication Section
auth_mode = st.sidebar.selectbox("Login / Register / Forgot Password / Logout", ["Login", "Register", "Forgot Password", "Logout", "Delete Account"])

if not st.session_state.logged_in:
    if auth_mode == "Register":
        st.subheader("Register")
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password (6-digit number)", type="password")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        secret = st.text_input("Secret Word (for password recovery)")

        if st.button("Register"):
            if len(password) != 6 or not password.isdigit():
                st.error("❌ Password must be a 6-digit number.")
            elif "@" not in email or "." not in email:
                st.error("❌ Invalid email format.")
            else:
                try:
                    register_user(name, email, password, gender, secret)
                    st.success("✅ Registration successful. You can now login.")
                except ValueError as ve:
                    st.error(f"❌ {ve}")  # Show error if email already exists

    elif auth_mode == "Login":
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            user = authenticate_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(f"✅ Welcome, {user[1]}!")
                st.rerun()  # Reload the page to reset the session state
            else:
                st.error("❌ Invalid email or password.")

    elif auth_mode == "Forgot Password":
        st.subheader("🔐 Forgot Password / Reset")
        email = st.text_input("📧 Enter your registered email")
        secret = st.text_input("🧠 Enter your secret word")
        new_password = st.text_input("🔑 Enter new password (6-digit number)", type="password")

        if st.button("Reset Password"):
            if len(new_password) != 6 or not new_password.isdigit():
                st.error("❌ Password must be a 6-digit number.")
            elif reset_password(email, secret, new_password):
                st.success("✅ Password reset successful. You can now log in with your new password.")
            else:
                st.error("❌ Incorrect email or secret word.")

else:
    st.sidebar.write(f"Logged in as: {st.session_state.user[1]}")

    if auth_mode == "Logout":
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.success("✅ Logged out successfully.")
            st.rerun()  # Reload the page to reset the session state

    elif auth_mode == "Delete Account":
        st.subheader("Delete Account")
        secret = st.text_input("Secret Word")

        if st.button("Delete My Account"):
            if delete_user(st.session_state.user[2], secret):
                st.success("✅ Account deleted successfully.")
                st.session_state.logged_in = False
                st.session_state.user = None
                st.rerun()  # Reload the page to reset the session state

# Main App: Expense Tracker
if not st.session_state.logged_in:
    st.warning("🔐 Please login first.")
    st.stop()  # Stop further execution if the user is not logged in.

user_id = st.session_state.user[0]
st.title(f"💸 {st.session_state.user[1]}'s Expense Tracker")

menu = ["Add Expense", "View Expenses", "Charts"]
choice = st.sidebar.radio("Menu", menu)

if choice == "Add Expense":
    st.subheader("➕ Add New Expense")
    with st.form("expense_form"):
        date = st.date_input("Date", value=datetime.date.today())
        category = st.selectbox("Category", ["Food", "Transport", "Bills", "Others"])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        description = st.text_input("Description")
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            add_expense(user_id, date, category, amount, description)
            st.success("✅ Expense added.")


elif choice == "View Expenses":
    st.subheader("📋 All Expenses")

    category_filter = st.selectbox("Filter by Category", ["All", "Food", "Transport", "Bills", "Others"])
    data = get_expenses(user_id) if category_filter == "All" else filter_expenses_by_category(user_id, category_filter)
    
    # Include ID for Edit/Delete
    df = pd.DataFrame(data, columns=["ID", "Date", "Category", "Amount", "Description"])
    st.dataframe(df)

    # Edit/Delete Section
    st.markdown("### ✏️&🗑️ Expense")
    if not df.empty:
        selected_id = st.selectbox("Select Expense ID", df["ID"].astype(str))
        action = st.radio("Action", ["Edit", "Delete"])

        # Get the row data
        selected_row = df[df["ID"] == int(selected_id)].iloc[0]

        if action == "Edit":
            with st.form("edit_form"):
                new_date = st.date_input("Date", pd.to_datetime(selected_row["Date"]))
                new_category = st.selectbox("Category", ["Food", "Transport", "Bills", "Others"], index=["Food", "Transport", "Bills", "Others"].index(selected_row["Category"]))
                new_amount = st.number_input("Amount", min_value=0.0, value=float(selected_row["Amount"]), format="%.2f")
                new_description = st.text_input("Description", value=selected_row["Description"])
                submit_edit = st.form_submit_button("Update")
                if submit_edit:
                    update_expense(int(selected_id), new_date, new_category, new_amount, new_description)
                    st.success("✅ Expense updated.")
                    st.rerun()

        elif action == "Delete":
            if st.button("Confirm Delete"):
                delete_expense(int(selected_id))
                st.success("🗑️ Expense deleted.")
                st.rerun()
    else:
        st.info("No expenses to edit or delete.")

    # Total Overview
    st.markdown("### 📆 Total Overview")
    col1, col2 = st.columns(2)

    with col1:
        selected_month = st.selectbox("Select Month", range(1, 13), format_func=lambda x: datetime.date(1900, x, 1).strftime('%B'))
        total_month = get_total_by_month(user_id, selected_month)
        st.metric(label="Monthly Total", value=f"{total_month:,.0f} MMK")

    with col2:
        selected_year = st.selectbox("Select Year", range(2022, 2031))
        total_year = get_total_by_year(user_id, selected_year)
        st.metric(label="Yearly Total", value=f"{total_year:,.0f} MMK")
 
 

elif choice == "Charts":
    st.subheader("📊 Expense Charts")

    category_summary = get_category_summary(user_id)
    if not category_summary.empty:
        pie_chart = px.pie(category_summary, names="Category", values="Total", title="Expenses by Category")
        st.plotly_chart(pie_chart, use_container_width=True)

        # Save as PNG in memory
        img_buf = io.BytesIO(pie_chart.to_image(format="png", engine="kaleido"))
        st.download_button("📥 Download Category Pie Chart", data=img_buf, file_name="category_chart.png", mime="image/png")
    else:
        st.info("No category data available.")

    monthly_summary = get_monthly_summary(user_id)
    if not monthly_summary.empty:
        bar_chart = px.bar(monthly_summary, x="Month", y="Total", title="Monthly Expenses")
        st.plotly_chart(bar_chart, use_container_width=True)

        img_buf = io.BytesIO(bar_chart.to_image(format="png", engine="kaleido"))
        st.download_button("📥 Download Monthly Bar Chart", data=img_buf, file_name="monthly_chart.png", mime="image/png")
    else:
        st.info("No monthly data available.")
