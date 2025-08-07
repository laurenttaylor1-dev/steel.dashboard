
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Steel Market Dashboard", layout="wide")

st.title("🧾 Steel Market Dashboard")

# ===== Exchange Rate Section =====
st.subheader("💱 Exchange Rate")
try:
    response = requests.get("https://api.exchangerate.host/latest?base=EUR&symbols=USD")
    data = response.json()
    exchange_rate = data["rates"]["USD"]
    timestamp = data["date"]
    st.markdown(f"**1 EUR = {exchange_rate:.4f} USD** (updated {timestamp})")
except Exception:
    st.warning("Could not fetch exchange rate. Using fallback rate.")
    exchange_rate = 1.10

# ===== Global Prices Table =====
st.subheader("📊 Latest Raw-Material Prices")

data = [
    {"Commodity": "Scrap (HMS 80/20)", "Region": "Turkey CFR", "Price_EUR": None, "Price_USD": 339.40, "Source": "https://www.indexmundi.com"},
    {"Commodity": "Scrap (E3 grade)", "Region": "Germany ex-works", "Price_EUR": 296.50, "Price_USD": 296.50 * exchange_rate, "Source": "https://www.indexmundi.com"},
    {"Commodity": "Scrap (mixed)", "Region": "Italy ex-works", "Price_EUR": 320.00, "Price_USD": 320.00 * exchange_rate, "Source": "https://www.indexmundi.com"},
    {"Commodity": "Scrap (HMS 80/20)", "Region": "US East Coast FOB", "Price_EUR": None, "Price_USD": 311.50, "Source": "https://www.indexmundi.com"},
    {"Commodity": "Coking Coal (global)", "Region": "Australia benchmark", "Price_EUR": None, "Price_USD": 105.04, "Source": "https://fred.stlouisfed.org"},
    {"Commodity": "HRC (Hot Rolled Coil)", "Region": "Western Europe ex-works", "Price_EUR": 545.00, "Price_USD": 545.00 * exchange_rate, "Source": "https://gmk.center"},
    {"Commodity": "HRC (Hot Rolled Coil)", "Region": "Italy ex-works", "Price_EUR": 527.50, "Price_USD": 527.50 * exchange_rate, "Source": "https://gmk.center"},
    {"Commodity": "HRC (Hot Rolled Coil)", "Region": "Southern Europe CIF", "Price_EUR": 500.00, "Price_USD": 500.00 * exchange_rate, "Source": "https://gmk.center"},
    {"Commodity": "HRC (Hot Rolled Coil)", "Region": "North America ex-works", "Price_EUR": None, "Price_USD": 970.00, "Source": "https://gmk.center"},
    {"Commodity": "HRC (Hot Rolled Coil)", "Region": "China FOB", "Price_EUR": None, "Price_USD": 490.00, "Source": "https://gmk.center"},
]

df = pd.DataFrame(data)
df["Price_USD"] = df["Price_USD"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "-")
df["Price_EUR"] = df["Price_EUR"].apply(lambda x: f"€{x:,.2f}" if pd.notnull(x) else "-")
df["Source"] = df["Source"].apply(lambda x: f"[link]({x})")

st.dataframe(df, use_container_width=True)

# ===== Excel Upload Section =====
st.subheader("📈 Price Trends from Uploaded Excel Files")

uploaded_files = st.file_uploader("Upload one or more Kallanish .xlsx files to visualize prices.", type="xlsx", accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            df_uploaded = pd.read_excel(uploaded_file, engine="openpyxl")
            st.markdown(f"**{uploaded_file.name}**")
            st.line_chart(df_uploaded.set_index(df_uploaded.columns[0]))
        except Exception as e:
            st.error(f"Could not read file {uploaded_file.name}: {e}")

# ===== Footer =====
st.markdown("---")
st.markdown("**Upcoming Features:**")
st.markdown("- 🧩 Live sync with Google Sheets")
st.markdown("- 📰 News integration from SteelOrbis, Shanghai Metals Market, Kallanish")
st.markdown("- 📱 Mobile-friendly manual price input form")
