import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from supabase import create_client

# Page Configuration
st.set_page_config(page_title="Civil Engineering BOQ System", layout="wide")

# 1. Database Connection Configuration
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Secure User Authentication Setups (TEST ACCOUNTS)
# NOTE: Passwords must be pre-hashed for streamlit-authenticator to work.
# Below, 'admin123' becomes '$2b$12$...' using standard bcrypt hashing.
credentials = {
    "usernames": {
        "civil_eng": {
            "name": "Juan Dela Cruz", 
            "password": "$2b$12$L7Cg4b.uYmZJ3vEwE9gOfe6gKjBvZKq8vYwXWvUu6z9l8q7M6fO2K"  # This is 'admin123'
        },
        "project_mgr": {
            "name": "Maria Clara", 
            "password": "$2b$12$L7Cg4b.uYmZJ3vEwE9gOfe6gKjBvZKq8vYwXWvUu6z9l8q7M6fO2K"  # This is 'admin123'
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name="boq_auth_cookie",
    key="signature_key_secret",
    cookie_expiry_days=30
)

# Render Login Widget
name, authentication_status, username = authenticator.login()

if authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
elif authentication_status:
    
    # --- MAIN SYSTEM RUNS ONLY IF LOGGED IN ---
    authenticator.logout('Logout', 'sidebar')
    st.title(f"🏗️ Project Cost Estimate System")
    st.subheader(f"Welcome back, Engr. {name}")
    
    # Initialize session state for active table
    if "boq_data" not in st.session_state:
        st.session_state.boq_data = pd.DataFrame(
            columns=["Item No.", "Item Description", "Unit", "Quantity", "Unit Cost", "Subtotal"]
        )

    # --- PROJECT DASHBOARD MANAGEMENT BOX ---
    st.markdown("### 🗄️ Project Dashboard Management")
    dash_col1, dash_col2 = st.columns(2)
    
    with dash_col1:
        st.subheader("💾 Save Active Project")
        proj_name = st.text_input("Enter Project Name to Save")
        if st.button("Save Current Table to Cloud"):
            if proj_name.strip() == "":
                st.error("Please enter a valid project name.")
            else:
                json_data = st.session_state.boq_data.to_json(orient="records")
                supabase.table("project_saves").insert({
                    "username": username,
                    "project_name": proj_name,
                    "boq_json": json_data
                }).execute()
                st.success(f"Project '{proj_name}' securely saved!")
                st.rerun()

    with dash_col2:
        st.subheader("📂 Reload Previous Calculations")
        response = supabase.table("project_saves").select("project_name, boq_json").eq("username", username).execute()
        saved_projects = response.data
        
        if saved_projects:
            proj_options = [p["project_name"] for p in saved_projects]
            selected_project = st.selectbox("Select a project to restore:", proj_options)
            
            if st.button("Load Selected Project"):
                chosen_data = next(p for p in saved_projects if p["project_name"] == selected_project)
                restored_df = pd.read_json(chosen_data["boq_json"])
                st.session_state.boq_data = restored_df
                st.success(f"Successfully loaded '{selected_project}'!")
                st.rerun()
        else:
            st.info("No saved projects found for your account.")

    st.markdown("---")
    
    # --- INPUT FIELDS & VALIDATION ---
    st.sidebar.header("📋 Item Input Form")
    item_desc = st.sidebar.text_input("Item Description", placeholder="e.g., Concrete Works")
    unit = st.sidebar.selectbox("Unit", ["sqm", "pcs", "cu.m", "kg", "linear m"])
    quantity = st.sidebar.number_input("Quantity", min_value=0.0, step=1.0, value=0.0)
    unit_cost = st.sidebar.number_input("Unit Cost", min_value=0.0, step=1.0, value=0.0)

    # --- BUTTON ACTIONS ---
    col1, col2 = st.sidebar.columns(2)

    if col1.button("➕ Add", use_container_width=True):
        if item_desc.strip() == "":
            st.sidebar.error("Description cannot be empty!")
        elif quantity <= 0 or unit_cost <= 0:
            st.sidebar.error("Quantity and Unit Cost must be greater than 0!")
        else:
            calculated_subtotal = quantity * unit_cost
            next_no = len(st.session_state.boq_data) + 1
            new_row = pd.DataFrame([{
                "Item No.": next_no,
                "Item Description": item_desc,
                "Unit": unit,
                "Quantity": quantity,
                "Unit Cost": unit_cost,
                "Subtotal": calculated_subtotal
            }])
            st.session_state.boq_data = pd.concat([st.session_state.boq_data, new_row], ignore_index=True)
            st.rerun()

    if col2.button("🧹 Clear", use_container_width=True):
        st.session_state.boq_data = pd.DataFrame(
            columns=["Item No.", "Item Description", "Unit", "Quantity", "Unit Cost", "Subtotal"]
        )
        st.rerun()

    if not st.session_state.boq_data.empty:
        st.sidebar.markdown("---")
        st.sidebar.header("🔧 Modify Existing Items")
        selected_no = st.sidebar.selectbox("Select Item No.", st.session_state.boq_data["Item No."].tolist())
        
        if st.sidebar.button("🔄 Update Selected Item", use_container_width=True):
            idx = st.session_state.boq_data[st.session_state.boq_data["Item No."] == selected_no].index
            if item_desc.strip() != "":
                st.session_state.boq_data.at[idx, "Item Description"] = item_desc
            if quantity > 0:
                st.session_state.boq_data.at[idx, "Quantity"] = quantity
            if unit_cost > 0:
                st.session_state.boq_data.at[idx, "Unit Cost"] = unit_cost
            
            st.session_state.boq_data.at[idx, "Subtotal"] = (
                st.session_state.boq_data.at[idx, "Quantity"] * st.session_state.boq_data.at[idx, "Unit Cost"]
            )
            st.success(f"Item {selected_no} updated!")
            st.rerun()

        if st.sidebar.button("❌ Delete Selected Item", use_container_width=True):
            st.session_state.boq_data = st.session_state.boq_data[st.session_state.boq_data["Item No."] != selected_no].reset_index(drop=True)
            st.session_state.boq_data["Item No."] = range(1, len(st.session_state.boq_data) + 1)
            st.rerun()

    # --- MAIN DISPLAY SCREEN ---
    grand_total = st.session_state.boq_data["Subtotal"].sum()
    st.metric(label="💰 Grand Total Project Cost", value=f"\u20b1{grand_total:,.2f}")

    st.markdown("### 📊 Bill of Quantities (BOQ) Spreadsheet Table")
    edited_df = st.data_editor(
        st.session_state.boq_data,
        num_rows="fixed",
        disabled=["Item No.", "Subtotal"], 
        hide_index=True,
        use_container_width=True,
        column_config={
            "Unit Cost": st.column_config.NumberColumn("Unit Cost", format="\u20b1%,.2f"),
            "Subtotal": st.column_config.NumberColumn("Subtotal", format="\u20b1%,.2f")
        }
    )

    if not edited_df.equals(st.session_state.boq_data):
        edited_df["Subtotal"] = edited_df["Quantity"] * edited_df["Unit Cost"]
        st.session_state.boq_data = edited_df
        st.rerun()
import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from supabase import create_client

# Page Configuration
st.set_page_config(page_title="Civil Engineering BOQ System", layout="wide")

# 1. Database Connection Configuration
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Secure User Authentication Setups (TEST ACCOUNTS)
# NOTE: Passwords must be pre-hashed for streamlit-authenticator to work.
# Below, 'admin123' becomes '$2b$12$...' using standard bcrypt hashing.
credentials = {
    "usernames": {
        "civil_eng": {
            "name": "Juan Dela Cruz", 
            "password": "$2b$12$L7Cg4b.uYmZJ3vEwE9gOfe6gKjBvZKq8vYwXWvUu6z9l8q7M6fO2K"  # This is 'admin123'
        },
        "project_mgr": {
            "name": "Maria Clara", 
            "password": "$2b$12$L7Cg4b.uYmZJ3vEwE9gOfe6gKjBvZKq8vYwXWvUu6z9l8q7M6fO2K"  # This is 'admin123'
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name="boq_auth_cookie",
    key="signature_key_secret",
    cookie_expiry_days=30
)

# Render Login Widget
name, authentication_status, username = authenticator.login()

if authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')
elif authentication_status:
    
    # --- MAIN SYSTEM RUNS ONLY IF LOGGED IN ---
    authenticator.logout('Logout', 'sidebar')
    st.title(f"🏗️ Project Cost Estimate System")
    st.subheader(f"Welcome back, Engr. {name}")
    
    # Initialize session state for active table
    if "boq_data" not in st.session_state:
        st.session_state.boq_data = pd.DataFrame(
            columns=["Item No.", "Item Description", "Unit", "Quantity", "Unit Cost", "Subtotal"]
        )

    # --- PROJECT DASHBOARD MANAGEMENT BOX ---
    st.markdown("### 🗄️ Project Dashboard Management")
    dash_col1, dash_col2 = st.columns(2)
    
    with dash_col1:
        st.subheader("💾 Save Active Project")
        proj_name = st.text_input("Enter Project Name to Save")
        if st.button("Save Current Table to Cloud"):
            if proj_name.strip() == "":
                st.error("Please enter a valid project name.")
            else:
                json_data = st.session_state.boq_data.to_json(orient="records")
                supabase.table("project_saves").insert({
                    "username": username,
                    "project_name": proj_name,
                    "boq_json": json_data
                }).execute()
                st.success(f"Project '{proj_name}' securely saved!")
                st.rerun()

    with dash_col2:
        st.subheader("📂 Reload Previous Calculations")
        response = supabase.table("project_saves").select("project_name, boq_json").eq("username", username).execute()
        saved_projects = response.data
        
        if saved_projects:
            proj_options = [p["project_name"] for p in saved_projects]
            selected_project = st.selectbox("Select a project to restore:", proj_options)
            
            if st.button("Load Selected Project"):
                chosen_data = next(p for p in saved_projects if p["project_name"] == selected_project)
                restored_df = pd.read_json(chosen_data["boq_json"])
                st.session_state.boq_data = restored_df
                st.success(f"Successfully loaded '{selected_project}'!")
                st.rerun()
        else:
            st.info("No saved projects found for your account.")

    st.markdown("---")
    
    # --- INPUT FIELDS & VALIDATION ---
    st.sidebar.header("📋 Item Input Form")
    item_desc = st.sidebar.text_input("Item Description", placeholder="e.g., Concrete Works")
    unit = st.sidebar.selectbox("Unit", ["sqm", "pcs", "cu.m", "kg", "linear m"])
    quantity = st.sidebar.number_input("Quantity", min_value=0.0, step=1.0, value=0.0)
    unit_cost = st.sidebar.number_input("Unit Cost", min_value=0.0, step=1.0, value=0.0)

    # --- BUTTON ACTIONS ---
    col1, col2 = st.sidebar.columns(2)

    if col1.button("➕ Add", use_container_width=True):
        if item_desc.strip() == "":
            st.sidebar.error("Description cannot be empty!")
        elif quantity <= 0 or unit_cost <= 0:
            st.sidebar.error("Quantity and Unit Cost must be greater than 0!")
        else:
            calculated_subtotal = quantity * unit_cost
            next_no = len(st.session_state.boq_data) + 1
            new_row = pd.DataFrame([{
                "Item No.": next_no,
                "Item Description": item_desc,
                "Unit": unit,
                "Quantity": quantity,
                "Unit Cost": unit_cost,
                "Subtotal": calculated_subtotal
            }])
            st.session_state.boq_data = pd.concat([st.session_state.boq_data, new_row], ignore_index=True)
            st.rerun()

    if col2.button("🧹 Clear", use_container_width=True):
        st.session_state.boq_data = pd.DataFrame(
            columns=["Item No.", "Item Description", "Unit", "Quantity", "Unit Cost", "Subtotal"]
        )
        st.rerun()

    if not st.session_state.boq_data.empty:
        st.sidebar.markdown("---")
        st.sidebar.header("🔧 Modify Existing Items")
        selected_no = st.sidebar.selectbox("Select Item No.", st.session_state.boq_data["Item No."].tolist())
        
        if st.sidebar.button("🔄 Update Selected Item", use_container_width=True):
            idx = st.session_state.boq_data[st.session_state.boq_data["Item No."] == selected_no].index
            if item_desc.strip() != "":
                st.session_state.boq_data.at[idx, "Item Description"] = item_desc
            if quantity > 0:
                st.session_state.boq_data.at[idx, "Quantity"] = quantity
            if unit_cost > 0:
                st.session_state.boq_data.at[idx, "Unit Cost"] = unit_cost
            
            st.session_state.boq_data.at[idx, "Subtotal"] = (
                st.session_state.boq_data.at[idx, "Quantity"] * st.session_state.boq_data.at[idx, "Unit Cost"]
            )
            st.success(f"Item {selected_no} updated!")
            st.rerun()

        if st.sidebar.button("❌ Delete Selected Item", use_container_width=True):
            st.session_state.boq_data = st.session_state.boq_data[st.session_state.boq_data["Item No."] != selected_no].reset_index(drop=True)
            st.session_state.boq_data["Item No."] = range(1, len(st.session_state.boq_data) + 1)
            st.rerun()

    # --- MAIN DISPLAY SCREEN ---
    grand_total = st.session_state.boq_data["Subtotal"].sum()
    st.metric(label="💰 Grand Total Project Cost", value=f"\u20b1{grand_total:,.2f}")

    st.markdown("### 📊 Bill of Quantities (BOQ) Spreadsheet Table")
    edited_df = st.data_editor(
        st.session_state.boq_data,
        num_rows="fixed",
        disabled=["Item No.", "Subtotal"], 
        hide_index=True,
        use_container_width=True,
        column_config={
            "Unit Cost": st.column_config.NumberColumn("Unit Cost", format="\u20b1%,.2f"),
            "Subtotal": st.column_config.NumberColumn("Subtotal", format="\u20b1%,.2f")
        }
    )

    if not edited_df.equals(st.session_state.boq_data):
        edited_df["Subtotal"] = edited_df["Quantity"] * edited_df["Unit Cost"]
        st.session_state.boq_data = edited_df
        st.rerun()
VV
