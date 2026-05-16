import streamlit as st
import pandas as pd

#page configuration
st.set_page_config(page_title="Civil Engineering BOQ system", layout="wide")
st.title("🏗Project Cost Estimate System")
st.subheader("Civil Engineering-Bill of Quantities(BOQ)")

#Initialize session state for the datatable
if "boq_data" not in st.session_state:
    st.session_state.boq_data=pd.DataFrame(columns=["Item No.", "Item Description", "Unit", "Quantity", "Unit Cost", "Subtotal"])

#Imput Fields & Validation
st.sidebar.header("Item Input Form")
item_desc=st.sidebar.text_input("Item Description". placeholder=="e.g.,Concrete")
unit=st.sidebar.selectbox("unit", ["sqm", "pcs", "cu.m", "kg"])

#Input validation: min_value=0.0 enforces negative values
quantity=st.sidebar.number_input("Quantity", min_value=0.0, step=1.0, value=0.0)
unit_cost=st.sidebar.number_input("Unit Cost", min_value=0.0, step=1.0, value=0.0)

#Instant computation helper
current_subtotal=quantity*unit_cost
st.sidebar.info(f"Instant Subtotal: \u20b1{current_subtotal:,.2f}")

#Button actions
col1, col2, col3=st.sidebar.columns(3)

#1.Add Item Button
if col1.button("➕ Add", use_container_width=True):
    if item_desc.strip() == "":
        st.sidebar.error("Description cannot be empty!")
    elif quantity <= 0 or unit_cost <= 0:
        st.sidebar.error("Quantity and Unit Cost must be greater than 0!")
    else:
        # Auto-numbering system based on length
        next_no = len(st.session_state.boq_data) + 1
        new_row = pd.DataFrame([{
            "Item No.": next_no,
            "Item Description": item_desc,
            "Unit": unit,
            "Quantity": quantity,
            "Unit Cost": unit_cost,
            "Subtotal": current_subtotal
        }])
        st.session_state.boq_data = pd.concat([st.session_state.boq_data, new_row], ignore_index=True)
        st.rerun()

# 2. Clear Table Button
if col2.button("🧹 Clear", use_container_width=True):
    st.session_state.boq_data = pd.DataFrame(
        columns=["Item No.", "Item Description", "Unit", "Quantity", "Unit Cost", "Subtotal"]
    )
    st.rerun()

# Operations for existing rows
if not st.session_state.boq_data.empty:
    st.sidebar.markdown("---")
    st.sidebar.header("🔧 Modify Existing Items")
    
    selected_no = st.sidebar.selectbox(
        "Select Item No.", 
        st.session_state.boq_data["Item No."].tolist()
    )
    
    # 3. Update Item Button
    if st.sidebar.button("🔄 Update Selected Item", use_container_width=True):
        idx = st.session_state.boq_data[st.session_state.boq_data["Item No."] == selected_no].index[0]
        if item_desc.strip() != "":
            st.session_state.boq_data.at[idx, "Item Description"] = item_desc
        if quantity > 0:
            st.session_state.boq_data.at[idx, "Quantity"] = quantity
        if unit_cost > 0:
            st.session_state.boq_data.at[idx, "Unit Cost"] = unit_cost
        
        # Recalculate subtotal
        st.session_state.boq_data.at[idx, "Subtotal"] = (
            st.session_state.boq_data.at[idx, "Quantity"] * st.session_state.boq_data.at[idx, "Unit Cost"]
        )
        st.success(f"Item {selected_no} updated successfully!")
        st.rerun()

    # 4. Delete Item Button
    if st.sidebar.button("❌ Delete Selected Item", use_container_width=True):
        st.session_state.boq_data = st.session_state.boq_data[
            st.session_state.boq_data["Item No."] != selected_no
        ].reset_index(drop=True)
        
        # Re-apply Auto-numbering system after deletion
        st.session_state.boq_data["Item No."] = range(1, len(st.session_state.boq_data) + 1)
        st.rerun()

# --- MAIN DISPLAY SCREEN (OUTPUTS) ---

# 5. Compute Total Cost (Instant & Automated Feature)
grand_total = st.session_state.boq_data["Subtotal"].sum()

# Displaying Grand Total KPI Card
st.metric(label="💰 Grand Total Project Cost", value=f"₱{grand_total:,.2f}")

st.markdown("### 📊 Bill of Quantities (BOQ) Spreadsheet Table")

# Feature: Editable table rows using data_editor
edited_df = st.data_editor(
    st.session_state.boq_data,
    num_rows="fixed",
    disabled=["Item No.", "Subtotal"], # Keep auto-calculations safe
    hide_index=True,
    use_container_width=True
)

# Sync edits back to session state and update subtotals automatically if edited inside the grid
if not edited_df.equals(st.session_state.boq_data):
    edited_df["Subtotal"] = edited_df["Quantity"] * edited_df["Unit Cost"]
    st.session_state.boq_data = edited_df
    st.rerun()
                                 
