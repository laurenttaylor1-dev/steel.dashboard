
import streamlit as st
import pandas as pd
import os
import datetime

st.set_page_config(layout="wide")
st.title("🧾 Steel Market Dashboard")
st.subheader("📈 Price Trends from Uploaded Excel Files")

# ------------- Upload XLSX files ----------------
uploaded_files = st.sidebar.file_uploader("Upload one or more XLSX files from Kallanish", type=["xlsx"], accept_multiple_files=True)

@st.cache_data
def load_kallanish_file(file):
    try:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        df = df.rename(columns={
            df.columns[0]: "Date",
            df.columns[1]: "Price"
        })
        df = df.dropna(subset=["Date", "Price"])
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        product_name = os.path.splitext(file.name)[0]
        df["Product"] = product_name
        return df
    except Exception as e:
        st.error(f"Could not read file {file.name}: {e}")
        return pd.DataFrame()

all_data = pd.DataFrame()
if uploaded_files:
    for file in uploaded_files:
        df = load_kallanish_file(file)
        all_data = pd.concat([all_data, df], ignore_index=True)

# ------------- Display Graphs ----------------
if not all_data.empty:
    products = all_data["Product"].unique()
    for product in products:
        product_df = all_data[all_data["Product"] == product]
        product_df = product_df.dropna(subset=["Date", "Price"])
        product_df = product_df.sort_values("Date")
        recent_df = product_df[product_df["Date"] > datetime.datetime.today() - datetime.timedelta(weeks=4)]
        
        st.markdown(f"### {product.replace('_', ' ')}")
        col1, col2 = st.columns([1, 3])

        with col1:
            latest = product_df.iloc[-1]
            st.metric("Latest Price", f"{latest['Price']}", f"As of {latest['Date'].date()}")
        
        with col2:
            if not recent_df.empty:
                st.line_chart(recent_df.set_index("Date")[["Price"]])
            else:
                st.warning("No data from the last 4 weeks available.")

else:
    st.info("Upload one or more Kallanish .xlsx files to visualize prices.")

# --------- Coming Next: Google Sheets + News Integration ---------
st.divider()
st.caption("Upcoming Features:")
st.markdown("- 🔄 Live sync with Google Sheets")
st.markdown("- 📰 News integration from SteelOrbis, Shanghai Metals Market, Kallanish")
st.markdown("- 📱 Mobile-friendly manual price input form")
