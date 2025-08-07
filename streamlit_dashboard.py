"""
Streamlit Steel Market Dashboard
================================

This Streamlit application provides a comprehensive dashboard for
steel‑industry professionals.  It combines live EUR→USD exchange
rates, a table of current raw‑material prices (iron ore, scrap,
coking coal and hot‑rolled coil) with hyperlinks to public source
articles, interactive charts for historical price series loaded from
Kallanish Excel files, and an expanded list of industry news
headlines.  Users can select the time horizon for each price chart
and remove individual news items from the feed.  The app also
automatically loads any historical price series placed in a ``data/``
directory within the repository, so there’s no need to upload those
files manually each time.

Key features
------------

* **Live exchange rate** – The dashboard fetches the latest EUR→USD
  rate from the free open.er‑api service.  If the call fails, the
  rate falls back to 1.00 and a warning is shown.
* **Latest raw‑material prices** – A static table summarises
  important commodity prices from public sources【294662876356880†L240-L265】,
  with European HRC values shown in both EUR/t and converted to
  USD/t.  Source URLs are provided as clickable links.
* **Historical price charts** – Users can select a time range (4 weeks,
  3 months, 6 months, 1 year, 2 years or 5 years) for the price
  graphs.  The app loads all price series from ``data/*.xlsx`` as
  well as any files uploaded via the sidebar and plots the selected
  range for each product.  The most recent price and date are shown
  above each chart.
* **News headlines** – The app retrieves up to 50 news items from
  GMK Center’s RSS feed and displays the first 20.  Users can remove
  individual headlines via a delete button; the list refreshes with
  additional articles to maintain length.  Removed headlines remain
  hidden for the current session.

To deploy this app on Streamlit Cloud, commit both ``streamlit_dashboard.py``
and the accompanying ``requirements.txt`` to your GitHub repository.
Ensure the ``data/`` folder (if used) is also part of the repo.  The
``requirements.txt`` file should include ``streamlit``, ``pandas``,
``numpy``, ``openpyxl``, ``requests``, ``beautifulsoup4``, ``lxml``
and ``python-dotenv`` (for future extensions).
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
from typing import Dict, List, Optional, Tuple

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import requests
import streamlit as st  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import xml.etree.ElementTree as ET


# -----------------------------------------------------------------------------
# Exchange rate helper
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def fetch_exchange_rate() -> Tuple[float, str]:
    """Return the latest EUR→USD rate and the date of the quote.

    Uses the open.er‑api.com service to fetch the latest rate.  If the
    API call fails for any reason, returns (1.0, "") as a fallback.

    Returns
    -------
    (rate, date)
        * rate : float – number of USD per EUR
        * date : str – ISO format date of the quote
    """
    url = "https://open.er-api.com/v6/latest/EUR"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data["rates"].get("USD", 1.0))
        # Example time string: "Thu, 07 Aug 2025 00:03:03 +0000"
        timestamp = data.get("time_last_update_utc", "")
        date_part = ""
        if timestamp:
            try:
                # Convert to date
                date_part = _dt.datetime.strptime(
                    timestamp.split(" +")[0], "%a, %d %b %Y %H:%M:%S"
                ).date().isoformat()
            except Exception:
                date_part = ""
        return rate, date_part
    except Exception:
        return 1.0, ""


# -----------------------------------------------------------------------------
# Latest price table helper
# -----------------------------------------------------------------------------

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
    data = [
        {
            "Commodity": "Iron Ore (62% Fe, CFR China)",
            "Region": "China",
            "Price_EUR": None,
            "Price_USD": 100.30,  # Aug 6 2025 price from TradingEconomics【294662876356880†L240-L265】
            "Source": "https://tradingeconomics.com/commodity/iron-ore",
        },
        {
            "Commodity": "Scrap (HMS 80/20)",
            "Region": "Turkey CFR",
            "Price_EUR": None,
            "Price_USD": 339.4,  # IndexBox June 2025【294662876356880†L240-L265】
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (E3 grade)",
            "Region": "Germany ex‑works",
            "Price_EUR": 296.5,  # IndexBox June 2025【294662876356880†L240-L265】
            "Price_USD": 296.5 * eur_usd,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (mixed)",
            "Region": "Italy ex‑works",
            "Price_EUR": 320.0,  # IndexBox June 2025【294662876356880†L240-L265】
            "Price_USD": 320.0 * eur_usd,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (HMS 80/20)",
            "Region": "US East Coast FOB",
            "Price_EUR": None,
            "Price_USD": 311.5,  # IndexBox June 2025【294662876356880†L240-L265】
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Coking Coal (global)",
            "Region": "Australia benchmark",
            "Price_EUR": None,
            "Price_USD": 105.04,  # FRED PCOALAUUSDM June 2025
            "Source": "https://fred.stlouisfed.org/series/PCOALAUUSDM",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Western Europe ex‑works",
            "Price_EUR": 545.0,  # GMK July 2025【685939607070121†screenshot】
            "Price_USD": 545.0 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Italy ex‑works",
            "Price_EUR": 527.5,  # GMK July 2025【685939607070121†screenshot】
            "Price_USD": 527.5 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Southern Europe CIF",
            "Price_EUR": 500.0,  # GMK July 2025【685939607070121†screenshot】
            "Price_USD": 500.0 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "North America ex‑works",
            "Price_EUR": None,
            "Price_USD": 970.0,  # GMK July 2025【685939607070121†screenshot】
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "China FOB",
            "Price_EUR": None,
            "Price_USD": 490.0,  # GMK July 2025【685939607070121†screenshot】
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
    ]
    df = pd.DataFrame(data)
    return df


# -----------------------------------------------------------------------------
# Kallanish Excel parsing helpers
# -----------------------------------------------------------------------------

def parse_kallanish_workbook(path: str) -> Dict[str, pd.DataFrame]:
    """Parse a Kallanish Excel file into multiple price series.

    Each Kallanish file contains a sheet called "Price Series".  Row 8
    (0‑indexed) holds the product names, and row 9 holds repeating
    column labels (Low, High, Avg) for each product.  Columns are
    grouped in threes: the first column after the date holds the Low
    price, the second holds High, and the third holds Avg.  We
    extract the Avg column for each product and return a dictionary
    mapping product names to a DataFrame with columns ``Date`` and
    ``Price``.

    Parameters
    ----------
    path : str
        Path to the Excel file on disk.

    Returns
    -------
    dict
        Mapping product name → DataFrame with ``Date`` and ``Price``.
    """
    try:
        # Read the entire sheet without headers
        df = pd.read_excel(path, sheet_name="Price Series", header=None, engine="openpyxl")
    except Exception:
        return {}
    # Locate the row containing 'Price Series' (product headers) and 'Dates'
    # According to the sample, row 8 (index 8) has product names; row 9 (index 9) has 'Dates', 'Low', 'High', 'Avg' repeating.
    # Determine the start index after 'Dates' row
    # Find 'Dates' in column 0
    try:
        dates_row = df[df[0] == "Dates"].index[0]
    except Exception:
        # Fall back to row 9
        dates_row = 9
    start_idx = dates_row + 1
    # Extract product names row (row before 'Dates')
    product_row = dates_row - 1
    # Column indices for product names start at 1 and repeat every 3 columns
    products: Dict[str, pd.DataFrame] = {}
    # Determine number of columns
    ncols = df.shape[1]
    # Step through columns in groups of 3: (Low, High, Avg)
    col = 1
    series_idx = 0
    while col + 2 < ncols:
        # Product name may span multiple rows; take non‑null value from row product_row
        name = df.iat[product_row, col]
        if pd.isna(name):
            # If this cell is NaN, try the next row above until a string is found
            # (some files may leave blank lines)
            tmp_row = product_row
            while tmp_row >= 0 and pd.isna(name):
                tmp_row -= 1
                name = df.iat[tmp_row, col] if tmp_row >= 0 else ""
        name = str(name).strip() if name is not None else ""
        # The Avg column is col+2
        avg_col = col + 2
        # Extract date and price columns
        data = df.iloc[start_idx:, [0, avg_col]].copy()
        data.columns = ["Date", "Price"]
        # Drop rows with NaN date or price
        data = data.dropna(subset=["Date", "Price"])
        # Convert to appropriate types
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data["Price"] = pd.to_numeric(data["Price"], errors="coerce")
        data = data.dropna(subset=["Date", "Price"])
        if name:
            products[name] = data
        col += 3
        series_idx += 1
    return products


def load_local_price_series(data_dir: str = "data") -> Dict[str, pd.DataFrame]:
    """Load all price series from .xlsx files in a directory.

    Scans ``data_dir`` for files ending with ``.xlsx`` and uses
    :func:`parse_kallanish_workbook` to extract each price series.  If
    multiple files contain the same product name, the series are
    concatenated and duplicates are removed by date (last entry wins).

    Parameters
    ----------
    data_dir : str, optional
        Directory relative to the app root containing historical data files.

    Returns
    -------
    dict
        Mapping product name → DataFrame of ``Date`` and ``Price``.
    """
    series: Dict[str, pd.DataFrame] = {}
    for path in glob.glob(os.path.join(data_dir, "*.xlsx")):
        file_series = parse_kallanish_workbook(path)
        for name, df in file_series.items():
            if name in series:
                # concatenate and drop duplicates by date
                combined = pd.concat([series[name], df])
                combined = combined.drop_duplicates(subset=["Date"], keep="last")
                combined = combined.sort_values("Date")
                series[name] = combined
            else:
                series[name] = df.sort_values("Date")
    return series


def load_uploaded_series(files) -> Dict[str, pd.DataFrame]:
    """Load series from files uploaded via Streamlit file uploader.

    Parameters
    ----------
    files : list
        List of uploaded file objects.

    Returns
    -------
    dict
        Mapping product name → DataFrame of ``Date`` and ``Price``.
    """
    series: Dict[str, pd.DataFrame] = {}
    if not files:
        return series
    for file in files:
        # Use file name as fallback product base if parse fails
        base_name = os.path.splitext(file.name)[0]
        try:
            # Save uploaded file to a temporary path in memory
            # Streamlit uploads produce file‑like objects
            file_series = parse_kallanish_workbook(file)
        except Exception:
            file_series = {}
        if not file_series:
            # Attempt to read first two columns as fallback (as in original code)
            try:
                df = pd.read_excel(file, sheet_name="Price Series", engine="openpyxl", header=None)
                # find 'Dates' row
                idx = df[df[0] == "Dates"].index[0]
                data = df.iloc[idx + 1:, [0, 1]].copy()
                data.columns = ["Date", "Price"]
                data = data.dropna(subset=["Date", "Price"])
                data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
                data["Price"] = pd.to_numeric(data["Price"], errors="coerce")
                data = data.dropna(subset=["Date", "Price"])
                file_series = {base_name: data}
            except Exception:
                file_series = {}
        # Merge into series dict
        for name, df in file_series.items():
            if name in series:
                combined = pd.concat([series[name], df])
                combined = combined.drop_duplicates(subset=["Date"], keep="last")
                series[name] = combined.sort_values("Date")
            else:
                series[name] = df.sort_values("Date")
    return series


# -----------------------------------------------------------------------------
# News headlines helpers
# -----------------------------------------------------------------------------

def fetch_gmk_headlines(limit: int = 50) -> List[Tuple[str, str]]:
    """Return a list of (title, link) tuples from GMK Center’s RSS feed.

    Parameters
    ----------
    limit : int
        Maximum number of items to return (default 50).

    Returns
    -------
    list
        Each tuple contains (title, link).  If parsing fails,
        returns an empty list.
    """
    feed_url = "https://gmk.center/en/feed/"
    headlines: List[Tuple[str, str]] = []
    try:
        resp = requests.get(feed_url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:limit]:
                title = item.findtext("title", default="").strip()
                link = item.findtext("link", default="").strip()
                if title and link:
                    headlines.append((title, link))
    except Exception:
        pass
    return headlines


# -----------------------------------------------------------------------------
# Streamlit app layout
# -----------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Steel Market Dashboard", layout="wide")
    st.title("Steel Market Dashboard")

    # Sidebar controls
    st.sidebar.header("Upload Kallanish .xlsx files (optional)")
    uploaded_files = st.sidebar.file_uploader(
        "Drag and drop files here", type=["xlsx"], accept_multiple_files=True
    )
    st.sidebar.markdown("---")
    # Time range selection for charts
    time_options = {
        "4 Weeks": _dt.timedelta(weeks=4),
        "3 Months": _dt.timedelta(days=90),
        "6 Months": _dt.timedelta(days=180),
        "1 Year": _dt.timedelta(days=365),
        "2 Years": _dt.timedelta(days=365 * 2),
        "5 Years": _dt.timedelta(days=365 * 5),
    }
    selected_range_label = st.sidebar.selectbox(
        "Select time range for price charts", list(time_options.keys()), index=0
    )
    selected_delta = time_options[selected_range_label]

    # Exchange rate
    eur_usd, rate_date = fetch_exchange_rate()
    st.subheader("Exchange Rate")
    if rate_date:
        st.markdown(f"**1 EUR = {eur_usd:.4f} USD** (quoted {rate_date})")
    else:
        st.warning("Could not fetch exchange rate. Using fallback rate of 1.00.")
        st.markdown(f"**1 EUR = {eur_usd:.4f} USD**")

    # Latest prices table
    st.subheader("Latest Raw‑Material Prices")
    latest_df = assemble_latest_prices(eur_usd)
    latest_df_display = latest_df.copy()
    latest_df_display["Price_EUR"] = latest_df_display["Price_EUR"].apply(
        lambda x: f"€{x:,.2f}" if pd.notnull(x) else "–"
    )
    latest_df_display["Price_USD"] = latest_df_display["Price_USD"].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) else "–"
    )
    latest_df_display["Source"] = latest_df_display["Source"].apply(
        lambda url: f"[link]({url})"
    )
    st.write(
        "European HRC prices are shown in EUR/t and converted to USD using the current exchange rate."
    )
    st.dataframe(
        latest_df_display[["Commodity", "Region", "Price_EUR", "Price_USD", "Source"]],
        hide_index=True,
    )

    # Price history charts
    st.subheader("Historical Price Trends")
    # Load local data from data directory
    local_series = load_local_price_series("data")
    # Load series from uploaded files (override local if same name)
    uploaded_series = load_uploaded_series(uploaded_files)
    # Merge uploaded into local
    all_series: Dict[str, pd.DataFrame] = local_series.copy()
    for name, df in uploaded_series.items():
        if name in all_series:
            combined = pd.concat([all_series[name], df])
            combined = combined.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
            all_series[name] = combined
        else:
            all_series[name] = df.sort_values("Date")
    if not all_series:
        st.info(
            "Upload Kallanish price files via the sidebar or place them in the `data/` folder of the repository to see price trends."
        )
    else:
        # Determine cutoff date based on selected range
        cutoff_date = _dt.datetime.today() - selected_delta
        for product_name, df in sorted(all_series.items()):
            # Filter by cutoff date
            recent_df = df[df["Date"] >= cutoff_date].copy()
            if recent_df.empty:
                st.warning(f"No data for {product_name} in selected time range.")
                continue
            latest_row = df.iloc[-1]
            latest_price = latest_row["Price"]
            latest_date = latest_row["Date"].date()
            st.markdown(
                f"**{product_name}** – Latest price ({latest_date}): {latest_price:.2f}"
            )
            # Prepare chart data
            chart_data = recent_df.copy().set_index("Date")
            st.line_chart(chart_data["Price"], height=250)

    # News headlines
    st.subheader("Steel Industry Headlines")
    # Fetch headlines up to 50 items
    headlines = fetch_gmk_headlines(limit=50)
    if 'removed_headlines' not in st.session_state:
        st.session_state['removed_headlines'] = set()
    # Filter out removed headlines
    available = [h for h in headlines if h[1] not in st.session_state['removed_headlines']]
    # Keep the first 20 available items
    display_count = 20
    to_display = available[:display_count]
    if not to_display:
        st.info("No headlines to display.")
    else:
        # Use columns to align title and delete button
        for title, link in to_display:
            cols = st.columns([20, 1])
            with cols[0]:
                st.markdown(f"- [{title}]({link})")
            with cols[1]:
                # Each delete button needs a unique key
                if st.button("✖", key=f"del_{link}"):
                    # Mark as removed and refresh
                    st.session_state['removed_headlines'].add(link)
                    st.experimental_rerun()

    # Footer: upcoming features
    st.markdown("---")
    st.write("### Upcoming Features:")
    st.write("- Live sync with Google Sheets")
    st.write("- News integration from SteelOrbis, Shanghai Metals Market and Kallanish")
    st.write("- Mobile‑friendly manual price input form")


if __name__ == "__main__":
    main()