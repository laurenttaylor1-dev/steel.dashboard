"""
Streamlit Steel Market Dashboard
================================

This Streamlit application provides a daily dashboard for steel‑industry
professionals.  It combines live EUR→USD exchange rates, a table of
important raw‑material prices (iron ore, scrap, coal and hot‑rolled
coil) with hyperlinks to source articles, and interactive charts for
historical price series uploaded from Kallanish Excel files.  The app
also displays the most recent steel‑industry headlines from GMK
Center’s RSS feed.

How it works
------------

* **Live exchange rate** – The app fetches the latest EUR→USD rate
  from the free exchangerate.host API.  If the API call fails, a
  fallback rate of 1.00 is used and the page displays a warning.
* **Latest raw‑material prices** – A static table summarises
  important commodity prices from public sources (Iron ore, scrap,
  coking coal, hot‑rolled coil).  European HRC prices are shown in
  both EUR/t and converted to USD/t using the current exchange rate.
* **Upload Kallanish history** – Users can drag and drop one or
  more Kallanish price series (.xlsx files) into the sidebar.  The
  dashboard extracts the date and the first price column from the
  “Price Series” worksheet and plots the last four weeks of data for
  each product.
* **News headlines** – The app pulls the five most recent news
  items from GMK Center’s English RSS feed and displays them as
  clickable links.

To deploy the app on Streamlit Cloud, make sure that the accompanying
``requirements.txt`` file is committed to your GitHub repository.
It should include the following dependencies: ``streamlit``, ``pandas``,
``openpyxl``, ``requests``, ``beautifulsoup4``, and ``lxml``.
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import Dict, List, Optional, Tuple

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import requests
import streamlit as st  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import xml.etree.ElementTree as ET


@st.cache_data(show_spinner=False)
def fetch_exchange_rate() -> Tuple[float, str]:
    """Return the latest EUR→USD rate and the date of the quote.

    Uses the exchangerate.host API to fetch the latest rate.  If the
    API call fails for any reason, returns (1.0, "") as a fallback.

    Returns
    -------
    (rate, date)
        * rate : float – number of USD per EUR
        * date : str – ISO format date of the quote
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "EUR", "symbols": "USD"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data["rates"]["USD"])
        date = data.get("date", "")
        return rate, date
    except Exception:
        return 1.0, ""


def assemble_latest_prices(eur_usd: float) -> pd.DataFrame:
    """Assemble a DataFrame of current raw‑material prices.

    Parameters
    ----------
    eur_usd : float
        Current EUR→USD rate used to convert euro prices to dollars.

    Returns
    -------
    pandas.DataFrame
        Table with columns: Commodity, Region, Price_EUR, Price_USD, Source.
    """
    # Hard‑coded price data drawn from public sources.  See report
    # citations for details【294662876356880†L240-L265】.  Euro values are
    # converted to USD using the supplied exchange rate.
    data: List[Dict[str, Optional[float]]] = [
        {
            "Commodity": "Iron Ore (62% Fe, CFR China)",
            "Region": "China",
            "Price_EUR": None,
            "Price_USD": 100.30,  # Aug 6 2025 price from TradingEconomics【294662876356880†L240-L265】
            "Source": "https://tradingeconomics.com/commodity/iron-ore",
        },
        {
            "Commodity": "Scrap (HMS 80/20)",
            "Region": "Turkey CFR",
            "Price_EUR": None,
            "Price_USD": 339.4,  # IndexBox June 2025【294662876356880†L240-L265】
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (E3 grade)",
            "Region": "Germany ex‑works",
            "Price_EUR": 296.5,  # IndexBox June 2025【294662876356880†L240-L265】
            "Price_USD": 296.5 * eur_usd,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (mixed)",
            "Region": "Italy ex‑works",
            "Price_EUR": 320.0,  # IndexBox June 2025【294662876356880†L240-L265】
            "Price_USD": 320.0 * eur_usd,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (HMS 80/20)",
            "Region": "US East Coast FOB",
            "Price_EUR": None,
            "Price_USD": 311.5,  # IndexBox June 2025【294662876356880†L240-L265】
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Coking Coal (global)",
            "Region": "Australia benchmark",
            "Price_EUR": None,
            "Price_USD": 105.04,  # FRED PCOALAUUSDM June 2025
            "Source": "https://fred.stlouisfed.org/series/PCOALAUUSDM",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Western Europe ex‑works",
            "Price_EUR": 545.0,  # GMK July 2025【685939607070121†screenshot】
            "Price_USD": 545.0 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Italy ex‑works",
            "Price_EUR": 527.5,  # GMK July 2025【685939607070121†screenshot】
            "Price_USD": 527.5 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Southern Europe CIF",
            "Price_EUR": 500.0,  # GMK July 2025【685939607070121†screenshot】
            "Price_USD": 500.0 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "North America ex‑works",
            "Price_EUR": None,
            "Price_USD": 970.0,  # GMK July 2025【685939607070121†screenshot】
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "China FOB",
            "Price_EUR": None,
            "Price_USD": 490.0,  # GMK July 2025【685939607070121†screenshot】
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
    ]
    df = pd.DataFrame(data)
    return df


def load_kallanish_excel(file) -> Optional[pd.DataFrame]:
    """Extract date and price columns from a Kallanish price series Excel file.

    The Kallanish xlsx files typically contain a worksheet named
    ``Price Series`` where the first column holds the date and the
    following columns contain one or more price series.  This function
    extracts the date column (renamed to ``Date``) and the first
    numeric price column (renamed to ``Price``).  Rows where the
    ``Date`` is not a valid date or where ``Price`` is missing are
    dropped.

    Parameters
    ----------
    file : UploadedFile
        Streamlit file object for the uploaded xlsx file.

    Returns
    -------
    pandas.DataFrame or None
        A DataFrame with columns ``Date`` (datetime) and ``Price``.
        If parsing fails, returns None.
    """
    try:
        # Read the 'Price Series' worksheet.  If using pandas <2.0, you
        # must specify engine='openpyxl'.  The first rows contain
        # metadata; the actual data starts around row 8 (index 8).
        df = pd.read_excel(file, sheet_name='Price Series', engine='openpyxl', header=None)
        # Find the row where the header 'Dates' appears in column 0
        header_row = df[df[0] == 'Dates'].index
        if len(header_row) == 0:
            return None
        start_idx = header_row[0] + 1
        # Slice the data starting from one row after 'Dates'
        data = df.iloc[start_idx:].copy()
        data = data[[0, 1]]  # first two columns: date and first price series
        data.columns = ['Date', 'Price']
        # Drop rows where date is NaN
        data = data.dropna(subset=['Date'])
        # Convert date strings to datetime
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
        # Convert price to numeric (may contain comma separators)
        data['Price'] = pd.to_numeric(data['Price'], errors='coerce')
        # Drop rows where either Date or Price is NaN
        data = data.dropna(subset=['Date', 'Price'])
        return data
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def fetch_gmk_headlines(limit: int = 5) -> List[Tuple[str, str]]:
    """Return a list of (title, link) tuples from GMK Center’s RSS feed.

    Parameters
    ----------
    limit : int
        Maximum number of items to return.

    Returns
    -------
    List[Tuple[str, str]]
        Each tuple contains (title, link).  The publication date is
        stripped from the link because the GMK feed includes the
        publication date in the article page itself.
    """
    feed_url = "https://gmk.center/en/feed/"
    headlines: List[Tuple[str, str]] = []
    try:
        resp = requests.get(feed_url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find('channel')
        if channel is not None:
            for item in channel.findall('item')[:limit]:
                title = item.findtext('title', default='').strip()
                link = item.findtext('link', default='').strip()
                headlines.append((title, link))
    except Exception:
        pass
    return headlines


def main() -> None:
    st.set_page_config(page_title="Steel Market Dashboard", layout="wide")
    st.title("Steel Market Dashboard")
    # Sidebar for file uploads
    st.sidebar.header("Upload one or more XLSX files from Kallanish")
    uploaded_files = st.sidebar.file_uploader(
        "Drag and drop files here", type=["xlsx"], accept_multiple_files=True
    )

    # Exchange rate section
    eur_usd, rate_date = fetch_exchange_rate()
    st.subheader("Exchange Rate")
    if rate_date:
        st.markdown(f"**1 EUR = {eur_usd:.4f} USD** (quoted {rate_date})")
    else:
        st.warning(
            "Could not fetch exchange rate. Using fallback rate of 1.00."
        )
        st.markdown(f"**1 EUR = {eur_usd:.4f} USD**")

    # Latest prices table
    st.subheader("Latest Raw‑Material Prices")
    latest_df = assemble_latest_prices(eur_usd)
    # Format price columns for display
    latest_df_display = latest_df.copy()
    latest_df_display['Price_EUR'] = latest_df_display['Price_EUR'].apply(
        lambda x: f"€{x:,.2f}" if pd.notnull(x) else '–'
    )
    latest_df_display['Price_USD'] = latest_df_display['Price_USD'].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) else '–'
    )
    latest_df_display['Source'] = latest_df_display['Source'].apply(
        lambda url: f"[link]({url})"
    )
    st.write(
        "European HRC prices are shown in EUR/t and converted to USD using the current exchange rate."
    )
    st.dataframe(
        latest_df_display[['Commodity', 'Region', 'Price_EUR', 'Price_USD', 'Source']],
        hide_index=True,
    )

    # Price trends from uploaded Excel files
    st.subheader("Price Trends from Uploaded Excel Files")
    if uploaded_files:
        for file in uploaded_files:
            # Derive product name from file name (strip extension and replace underscores)
            name = os.path.splitext(file.name)[0]
            # Attempt to load the Excel data
            data = load_kallanish_excel(file)
            if data is None or data.empty:
                st.error(
                    f"Could not read file {file.name}: please ensure it contains a 'Price Series' sheet."
                )
                continue
            # Keep only last four weeks of data
            cutoff = _dt.datetime.today() - _dt.timedelta(weeks=4)
            recent = data[data['Date'] >= cutoff]
            if recent.empty:
                st.warning(f"No data in the last four weeks for {name}.")
                continue
            latest_price = recent.iloc[-1]['Price']
            latest_date = recent.iloc[-1]['Date'].date()
            st.markdown(f"**{name}** – Latest price ({latest_date}): {latest_price:.2f}")
            chart_df = recent.set_index('Date')
            st.line_chart(chart_df['Price'])
    else:
        st.info("Upload one or more Kallanish .xlsx files to visualise prices.")

    # News headlines
    st.subheader("Steel Industry Headlines")
    headlines = fetch_gmk_headlines()
    if headlines:
        for title, link in headlines:
            st.markdown(f"- [{title}]({link})")
    else:
        st.warning("Could not retrieve news headlines at this time.")

    # Footer: upcoming features
    st.markdown("---")
    st.write("### Upcoming Features:")
    st.write("- Live sync with Google Sheets")
    st.write("- News integration from SteelOrbis, Shanghai Metals Market and Kallanish")
    st.write("- Mobile‑friendly manual price input form")


if __name__ == "__main__":
    main()