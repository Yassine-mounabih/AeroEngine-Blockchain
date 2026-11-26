import os
import streamlit as st
import requests

st.set_page_config(
    page_title="AeroEngine Blockchain",
    page_icon="✈️",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:3000")

st.title("✈️ AeroEngine Blockchain")
st.caption("Aircraft Engine Maintenance and Traceability")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Engine Registry",
        "Register Engine",
        "Maintenance Requests",
        "Record Maintenance",
        "Transfer Engine",
        "Engine History"
    ]
)

st.sidebar.divider()

try:
    response = requests.get(
        f"{API_URL}/api/health",
        timeout=5
    )
    response.raise_for_status()
    health = response.json()

    st.sidebar.success("Backend connected")

    if health.get("blockchain") == "connected":
        st.sidebar.success("Blockchain connected")
    else:
        st.sidebar.warning("Blockchain not connected")

except (requests.RequestException, ValueError):
    health = {}
    st.sidebar.error("Backend unavailable")

if page == "Dashboard":
    st.header("System Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Backend", health.get("backend", "Offline"))
    col2.metric("Blockchain", health.get("blockchain", "Unknown"))
    col3.metric("Channel", health.get("channel", "Unavailable"))
    col4.metric("Chaincode", health.get("chaincode", "Unavailable"))

    st.divider()

    st.subheader("Participating Organizations")

    org1, org2 = st.columns(2)

    with org1:
        st.info("Org1MSP — Airline Company")
        st.write("Engine registration and maintenance requests.")

    with org2:
        st.info("Org2MSP — Maintenance Company")
        st.write("Maintenance interventions and engine status updates.")

else:
    st.header(page)
    st.info("This feature is under development.")

