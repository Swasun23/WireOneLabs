import streamlit as st
import requests
import pandas as pd
from config import settings

# Define the base URL for the Falcon API
BASE_URL = settings.API_ENDPOINT_BASE_URL

st.title("Delivery Assignment System")

# Tabs for different functionalities
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Worker Check-In",
    "Order Allocation",
    "Agents Info",
    "Agent Orders",
    "Orders_left",
    "Worker Check-Out",
    "Orders upload"
])

with tab1:
    st.header("Worker Check-In")
    if st.button("Randomly Mark Agents as Checked-In"):
        with st.spinner("Marking agents as checked-in..."):
            response = requests.post(f"{BASE_URL}/checkin/")
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error("Failed to check in agents!")

with tab2:
    st.header("Order Allocation")
    if st.button("Trigger Order Allocation"):
        with st.spinner("Allocating orders..."):
            response = requests.post(f"{BASE_URL}/allocate/")
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error("Failed to trigger order allocation!")

with tab3:
    st.header("Agents Info")
    if st.button("Get Agents Info"):
        with st.spinner("Fetching agents info..."):
            response = requests.get(f"{BASE_URL}/agent_info/")
            if response.status_code == 200:
                agents_info = response.json()["agents"]
                df = pd.DataFrame(agents_info)
                
                st.write("### Agents Info:")
                st.dataframe(df)
                
                total_no_orders = response.json()["total_no_of_orders"]
                cost_per_order = response.json()["cost_per_order"]
                if total_no_orders > 0:
                    st.write(f"## Total no of orders this day:{total_no_orders}")
                    st.write(f"## cost per order:{cost_per_order}")
                else:
                    st.write("## No orders allocated!")    
            else:
                st.error("Failed to fetch agents info!")

with tab4:
    st.header("Agent Orders")
    agent_id = st.number_input("Enter Agent ID", min_value=1, step=1)
    if st.button("Get Orders for Agent"):
        with st.spinner("Fetching agent's orders..."):
            response = requests.get(f"{BASE_URL}/agent_orders/{agent_id}")
            if response.status_code == 200:
                orders = response.json()["orders"]
                if orders:
                    orders_df = pd.DataFrame(orders)
                    st.write(f"### Orders for Agent {agent_id}:")
                    st.dataframe(orders_df)
                else:
                    st.info(f"No orders found for agent {agent_id}.")
            else:
                st.error("Failed to fetch orders for the agent!")

with tab6:
    st.header("Worker Check-Out")
    if st.button("Mark All Agents as Checked-Out"):
        with st.spinner("Marking agents as checked-out..."):
            response = requests.post(f"{BASE_URL}/checkout/")
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error("Failed to check out agents!")

with tab5:
    st.title("Undelivered Orders")
    
    try:
        # Fetch data from the `/orders_left/` endpoint
        response = requests.get(f"{BASE_URL}/orders_left/")
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Process JSON data
        orders_info = response.json()["orders"]  # Assuming your API returns JSON
        
        if orders_info:
            # Convert the data into a DataFrame for display
            df = pd.DataFrame(orders_info)
            
            # Display the DataFrame as a table
            st.subheader("Undelivered Orders Table")
            st.dataframe(df)  # Interactive table
            
        else:
            st.info("No undelivered orders found.")

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
    except ValueError as e:
        st.error(f"Error processing data: {e}")

with tab7:
    st.title("Upload Orders to Database")

    # Create a button to trigger the order upload
    if st.button("Upload Orders"):
        try:
            # Make a POST request to the /upload_orders endpoint
            response = requests.post(f"{BASE_URL}/upload_orders")
            
            # Parse the response
            if response.status_code == 200:
                st.success(response.json().get("message", "Orders uploaded successfully!"))
            else:
                st.error(response.json().get("message", "Failed to upload orders."))
        except Exception as e:
            # Handle connection or unexpected errors
            st.error(f"An error occurred: {e}")