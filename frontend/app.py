import os
import requests
import streamlit as st

st.set_page_config(
    page_title="AeroEngine Blockchain",
    page_icon="✈️",
    layout="wide"
)

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:3000"
).rstrip("/")

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None


def logout():
    st.session_state.token = None
    st.session_state.user = None


def login_page():
    st.title("✈️ AeroEngine Blockchain")
    st.caption("Aircraft Engine Maintenance and Traceability")

    left, center, right = st.columns([1, 2, 1])

    with center:
        st.subheader("Sign in")

        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Sign in",
                use_container_width=True
            )

        if submitted:
            if not username or not password:
                st.warning("Enter your username and password.")
                return

            try:
                response = requests.post(
                    f"{API_URL}/auth/login",
                    json={
                        "username": username,
                        "password": password
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data["token"]
                    st.session_state.user = data["user"]
                    st.rerun()

                elif response.status_code == 401:
                    st.error("Invalid username or password.")

                elif response.status_code == 429:
                    st.error("Too many login attempts. Try again later.")

                else:
                    st.error("Authentication service unavailable.")

            except (requests.RequestException, ValueError, KeyError):
                st.error("Unable to connect to the backend.")

        st.divider()
        st.caption("Authorized organizations")
        st.info("Org1MSP — Airline Company")
        st.info("Org2MSP — Maintenance Company")


if not st.session_state.token:
    login_page()
    st.stop()


headers = {
    "Authorization": f"Bearer {st.session_state.token}"
}

try:
    response = requests.get(
        f"{API_URL}/auth/me",
        headers=headers,
        timeout=5
    )

    if response.status_code == 401:
        logout()
        st.rerun()

    response.raise_for_status()
    st.session_state.user = response.json()["user"]

except (requests.RequestException, ValueError, KeyError):
    st.error("Unable to verify your session.")
    st.button("Sign out", on_click=logout)
    st.stop()


user = st.session_state.user
organization = user["organization"]

st.sidebar.title("AeroEngine")
st.sidebar.divider()

st.sidebar.write(f"**User:** {user['username']}")
st.sidebar.write(f"**Organization:** {organization}")

if organization == "Org1MSP":
    st.sidebar.info("Airline Company")

    pages = [
        "Dashboard",
        "Engine Registry",
        "Register Engine",
        "Maintenance Requests",
        "Transfer Engine",
        "Engine History"
    ]

elif organization == "Org2MSP":
    st.sidebar.info("Maintenance Company")

    pages = [
        "Dashboard",
        "Engine Registry",
        "Maintenance Requests",
        "Record Maintenance",
        "Update Engine Status",
        "Transfer Engine",
        "Engine History"
    ]

else:
    st.error("Unauthorized organization.")
    st.button("Sign out", on_click=logout)
    st.stop()


page = st.sidebar.radio("Navigation", pages)

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


st.sidebar.button(
    "Sign out",
    on_click=logout,
    use_container_width=True
)

st.title("✈️ AeroEngine Blockchain")
st.caption("Aircraft Engine Maintenance and Traceability")

if page == "Dashboard":

    st.header("System Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Backend", health.get("backend", "Offline"))
    col2.metric("Blockchain", health.get("blockchain", "Unknown"))
    col3.metric("Channel", health.get("channel", "Unavailable"))
    col4.metric("Chaincode", health.get("chaincode", "Unavailable"))

    st.divider()

    st.subheader("Organization Dashboard")

    if organization == "Org1MSP":
        st.info("Airline Company Dashboard")
        st.write(
            "Register aircraft engines, request maintenance, "
            "transfer custody and consult engine history."
        )

    else:
        st.info("Maintenance Company Dashboard")
        st.write(
            "Consult engines, perform maintenance, "
            "update engine status and return engine custody."
        )

    st.warning("Business transactions require Fabric integration.")

else:
    st.header(page)
    st.info("This feature is under development.")

