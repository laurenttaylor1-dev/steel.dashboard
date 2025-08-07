"""
Streamlit Steel Dashboard
=========================

This Streamlit application presents a dashboard tailored for the steel
industry.  It pulls together currency data, commodity prices,
industry headlines and a summary of key events.  Users can also
upload their own price history (e.g. from Kallanish) to enrich the
graphs.  The goal is to offer a convenient, self‑updating overview
that can serve as a foundation for newsletters or internal reports.

Data sources
------------

* **Exchange rates:** EUR→USD rates are fetched from the open
  exchange rate API at `open.er-api.com`.
* **Iron ore price:** Scraped from the Financial Times commodity
  page (Iron Ore 62 % Fe CFR China).  The current value is
  referenced in the accompanying report【294662876356880†L244-L265】.
* **Scrap, coal and HRC prices:** Hard‑coded values drawn from
  publicly available reports (e.g., IndexBox’s June 2025 scrap
  overview【294662876356880†L244-L265】 and GMK Center’s July 2025
  HRC article【685939607070121†screenshot】).  These values should be
  updated manually when new data becomes available.
* **Headlines:** Pulled from GMK Center’s English RSS feed.

To deploy this app on Streamlit Cloud you’ll need a free account at
`https://streamlit.io`.  After signing up, you can create a new app
repository (for example on GitHub), commit this file there and then
configure Streamlit Cloud to run it.  Streamlit Cloud will handle
hosting and daily updates automatically if the code refreshes data
whenever the page is loaded.
"""

from __future__ import annotations

import datetime as _dt
from typing import List, Tuple, Optional

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


def fetch_exchange_rate() -> Tuple[float, str]:
    """Fetch the latest EUR→USD exchange rate using open.er-api."""
    api_url = "https://open.er-api.com/v6/latest/EUR"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = float(data["rates"].get("USD", 0.0))
        timestamp = data.get("time_last_update_utc", "")
    except Exception:
        rate, timestamp = float("nan"), ""
    return rate, timestamp


def fetch_iron_ore_price() -> Optional[float]:
    """Scrape the current iron‑ore price from Financial Times."""
    url = "https://markets.ft.com/data/commodities/tearsheet/summary?c=Iron%20Ore"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        price_span = soup.find("span", class_="mod-ui-data-list__value")
        if price_span:
            return float(price_span.get_text(strip=True).replace(",", ""))
    except Exception:
        pass
    return None


def fetch_gmk_headlines(limit: int = 5) -> List[Tuple[str, str, str]]:
    """Return a list of (title, date, link) tuples from GMK Center’s RSS feed."""
    import xml.etree.ElementTree as ET
    feed_url = "https://gmk.center/en/feed/"
    headlines: List[Tuple[str, str, str]] = []
    try:
        resp = requests.get(feed_url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:limit]:
                title = item.findtext("title", default="").strip()
                pub_date_raw = item.findtext("pubDate", default="").strip()
                # Extract date part (e.g. "Thu, 07 Aug 2025 ..." → "07 Aug 2025")
                pub_date = " ".join(pub_date_raw.split()[1:4]) if pub_date_raw else ""
                link = item.findtext("link", default="").strip()
                headlines.append((title, pub_date, link))
    except Exception:
        pass
    return headlines


def default_price_data(eur_usd_rate: float) -> pd.DataFrame:
    """Create a DataFrame with the latest prices and reference links."""
    # Hard‑coded prices and their sources (update manually when new data is
    # available).  Euro prices are converted to USD for the USD column.
    data = [
        {
            "Commodity": "Iron Ore (62% Fe, CFR China)",
            "Region": "China",
            "Price_EUR": None,
            "Price_USD": fetch_iron_ore_price(),
            "Source": "https://markets.ft.com/data/commodities/tearsheet/summary?c=Iron%20Ore",
        },
        {
            "Commodity": "Scrap (HMS 80/20)",
            "Region": "Turkey CFR",
            "Price_EUR": None,
            "Price_USD": 339.4,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (E3 grade)",
            "Region": "Germany ex-works",
            "Price_EUR": 296.5,
            "Price_USD": 296.5 * eur_usd_rate,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (mixed)",
            "Region": "Italy ex-works",
            "Price_EUR": 320.0,
            "Price_USD": 320.0 * eur_usd_rate,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (HMS 80/20)",
            "Region": "US East Coast FOB",
            "Price_EUR": None,
            "Price_USD": 311.5,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Coking Coal (global)",
            "Region": "Australia benchmark",
            "Price_EUR": None,
            "Price_USD": 105.04349,
            "Source": "https://fred.stlouisfed.org/series/PCOALAUUSDM",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Western Europe ex-works",
            "Price_EUR": 545.0,
            "Price_USD": 545.0 * eur_usd_rate,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Italy ex-works",
            "Price_EUR": 527.5,
            "Price_USD": 527.5 * eur_usd_rate,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Southern Europe CIF",
            "Price_EUR": 500.0,
            "Price_USD": 500.0 * eur_usd_rate,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "North America ex-works",
            "Price_EUR": None,
            "Price_USD": 970.0,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "China FOB",
            "Price_EUR": None,
            "Price_USD": 490.0,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
    ]
    df = pd.DataFrame(data)
    return df


def generate_dummy_history(current: float, weeks: int = 4) -> pd.Series:
    """Generate a dummy 4‑week history for demonstration purposes.

    Since we don’t have official weekly series for every commodity,
    this helper function synthesizes a simple linear trend that ends at
    the current value.  Replace this logic by reading real data if
    available (e.g. from a CSV file uploaded by the user).
    """
    # Create a small random walk around the current price
    import numpy as np
    end = current if current is not None else np.nan
    # Assume weekly changes of up to ±3%
    changes = np.random.uniform(-0.03, 0.03, size=weeks)
    values = [end]
    for change in reversed(changes):
        values.append(values[-1] / (1 + change))
    values = list(reversed(values[:-1]))  # Drop the last duplicate
    return pd.Series(values, index=[_dt.date.today() - _dt.timedelta(weeks=i) for i in range(weeks, 0, -1)])


def load_user_history(uploaded_file) -> pd.DataFrame:
    """Parse an uploaded CSV or Excel file containing price history.

    The file should contain columns: Date, Commodity, Region, Price,
    Currency (EUR or USD).  Dates should be parseable by pandas.
    """
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except Exception:
        return pd.DataFrame()


def build_dashboard() -> None:
    """Assemble the Streamlit dashboard layout."""
    st.title("Steel Market Dashboard")
    st.write("\n")
    # Fetch data
    eur_usd_rate, rate_timestamp = fetch_exchange_rate()
    # Header with currency info
    st.subheader("Exchange Rate")
    if pd.notnull(eur_usd_rate):
        st.markdown(f"**1 EUR = {eur_usd_rate:.4f} USD** (updated {rate_timestamp})")
    else:
        st.markdown("Could not retrieve exchange rate.")

    # Latest prices table
    df_latest = default_price_data(eur_usd_rate)
    st.subheader("Latest Raw‑Material Prices")
    st.write(
        "European HRC prices are shown in EUR/t and converted to USD using the current exchange rate."
    )
    # Display as a table with hyperlinks in Source column
    df_display = df_latest.copy()
    # Format price columns
    df_display["Price_EUR"] = df_display["Price_EUR"].apply(
        lambda x: f"€{x:,.2f}" if pd.notnull(x) else "–"
    )
    df_display["Price_USD"] = df_display["Price_USD"].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) else "–"
    )
    # Render clickable links
    df_display["Source"] = df_display["Source"].apply(
        lambda url: f"[link]({url})" if url else ""
    )
    st.dataframe(df_display[["Commodity", "Region", "Price_EUR", "Price_USD", "Source"]])

    # Price history section
    st.subheader("Price Evolution (Past 4 Weeks)")
    st.write(
        "Upload your own CSV or Excel file to replace the dummy history. \n"
        "The file should have columns: Date, Commodity, Region, Price, Currency."
    )
    uploaded = st.file_uploader("Upload price history (optional)", type=["csv", "xlsx", "xls"])
    user_history = load_user_history(uploaded)
    for _, row in df_latest.iterrows():
        col_title = f"{row['Commodity']} – {row['Region']}"
        st.markdown(f"### {col_title}")
        current_price = row["Price_USD"] if row["Price_USD"] and pd.notnull(row["Price_USD"]) else row["Price_EUR"]
        # Determine history
        if not user_history.empty:
            # Filter user history by commodity and region
            mask = (
                (user_history["Commodity"] == row["Commodity"])
                & (user_history["Region"] == row["Region"])
            )
            hist_df = user_history.loc[mask, ["Date", "Price", "Currency"]].copy()
            hist_df = hist_df.sort_values("Date")
        else:
            # Generate dummy data
            hist_series = generate_dummy_history(current_price or 0.0)
            hist_df = hist_series.reset_index()
            hist_df.columns = ["Date", "Price"]
            hist_df["Currency"] = "USD" if row["Price_USD"] else "EUR"
        # Create line chart
        chart_data = pd.DataFrame({
            "Date": hist_df["Date"],
            "Price": hist_df["Price"]
        })
        st.line_chart(chart_data.rename(columns={"Price": ""}).set_index("Date"))

    # Headlines
    st.subheader("Key Steel Industry Headlines")
    headlines = fetch_gmk_headlines()
    if headlines:
        for title, date, link in headlines:
            st.markdown(f"- [{title}]({link}) ({date})")
    else:
        st.write("Could not retrieve headlines.")

    # Summary table of key events
    st.subheader("Brief Summary of Key Global Steel Events")
    summary_events = [
        {
            "Date": "2025-07-24",
            "Event": "Turkey’s HMS 80/20 scrap prices slipped 1.7% to $339.4/t CFR while E3 scrap in Germany stabilised at €296.5/t",
        },
        {
            "Date": "2025-08-01",
            "Event": "Western Europe HRC dropped to €545/t ex‑works and Italy to €527.5/t while China’s FOB price rose to $490/t",
        },
        {
            "Date": "2025-06-30",
            "Event": "Global coal (Australia benchmark) hovered around $105/t as reported by the IMF/FRED data",
        },
    ]
    st.table(pd.DataFrame(summary_events))


if __name__ == "__main__":
    build_dashboard()