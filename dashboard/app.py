"""Streamlit dashboard entrypoint. Talks only to Postgres/API -- no
dependency on training code in src/public_pulse.
"""

import streamlit as st

st.title("Public Pulse")
st.write("Civic-intelligence dashboard for Sri Lankan media discourse.")
