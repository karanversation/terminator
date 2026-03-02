"""Shared cached data loader for all networth pages."""
import streamlit as st
from networth.loader import load_all_holdings


@st.cache_data(ttl=300, show_spinner=False)
def get_networth_data():
    return load_all_holdings()
