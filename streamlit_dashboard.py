"""
Streamlit Steel Market Dashboard – Version 4
===========================================

This version enhances the previous dashboard with configurable
multi‑series charts and a historical exchange rate graph.  Users
can select which price series to combine into two separate graphs,
choose the time horizon for those graphs (4 weeks, 3 months,
6 months, 1 year, 2 years or 5 years) and see the latest price for
each selected series.  The Y‑axis automatically adjusts to the
selected data range, showing roughly 20 % headroom below the
minimum price and 5 % above the maximum.  A dedicated exchange
rate chart visualises EUR→USD movements over the last 7 days by
default (or another range if selected).

Core components:

* **Exchange rate & history:**  Fetches the latest EUR→USD rate via
  open.er‑api.com and retrieves historical rates from
  exchangerate.host for the selected period.  Displays a small line
  chart and the most recent value.
* **Price table:**  Summarises current prices for iron ore, scrap,
  coking coal and HRC with sources【294662876356880†L240-L265】【685939607070121†screenshot】.
* **Multi‑series price charts:**  Combines any selected product
  series into two graphs.  Data is loaded automatically from
  ``data/*.xlsx`` and from uploaded files.
* **News feed:**  Displays up to 20 headlines from GMK Center with
  delete buttons to hide unwanted stories; additional stories
  replenish the list on deletion.

Place your historical Kallanish Excel files in a ``data/`` folder in
the repository.  Upload new files via the sidebar to append or
override existing series.  Deploy this app on Streamlit Cloud by
setting the main file to ``streamlit_dashboard_v4.py``.
"""

from __future__ import annotations

import datetime as _dt
import glob
import os
from typing import Dict, List, Optional, Tuple

import altair as alt  # type: ignore
import numpy as np  # type: ignore
import pandas as pd  # type: ignore
import requests
import streamlit as st  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import xml.etree.ElementTree as ET


# -----------------------------------------------------------------------------
# Exchange rate helpers
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def fetch_exchange_rate() -> Tuple[float, str]:
    """Return the latest EUR→USD rate and the date of the quote.

    Uses the open.er‑api.com service.  Returns (1.0, "") on error.
    """
    url = "https://open.er-api.com/v6/latest/EUR"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rate = float(data.get("rates", {}).get("USD", 1.0))
        timestamp = data.get("time_last_update_utc", "")
        date_part = ""
        if timestamp:
            try:
                date_part = _dt.datetime.strptime(
                    timestamp.split(" +")[0], "%a, %d %b %Y %H:%M:%S"
                ).date().isoformat()
            except Exception:
                date_part = ""
        return rate, date_part
    except Exception:
        return 1.0, ""


@st.cache_data(show_spinner=False)
def fetch_exchange_rate_series(start_date: _dt.date, end_date: _dt.date) -> Optional[pd.DataFrame]:
    """Fetch a time series of EUR→USD exchange rates via exchangerate.host.

    Returns a DataFrame with columns ``Date`` and ``Rate`` or ``None`` on
    error.  The service does not require an API key.
    """
    base_url = "https://api.exchangerate.host/timeseries"
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "base": "EUR",
        "symbols": "USD",
    }
    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rates = data.get("rates", {})
        records: List[Tuple[_dt.date, float]] = []
        for date_str, value in rates.items():
            usd = value.get("USD")
            if usd is None:
                continue
            try:
                dt = _dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                records.append((dt, float(usd)))
            except Exception:
                continue
        if not records:
            return None
        df = pd.DataFrame(records, columns=["Date", "Rate"]).sort_values("Date")
        return df
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Latest price table helper
# -----------------------------------------------------------------------------

def assemble_latest_prices(eur_usd: float) -> pd.DataFrame:
    """Assemble a DataFrame of current raw‑material prices.

    European HRC prices are converted to USD using the provided rate.
    """
    data = [
        {
            "Commodity": "Iron Ore (62% Fe, CFR China)",
            "Region": "China",
            "Price_EUR": None,
            "Price_USD": 100.30,
            "Source": "https://tradingeconomics.com/commodity/iron-ore",
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
            "Region": "Germany ex‑works",
            "Price_EUR": 296.5,
            "Price_USD": 296.5 * eur_usd,
            "Source": "https://www.indexbox.io/blog/june-2025-scrap-market-shows-signs-of-stabilization-amidst-global-challenges/",
        },
        {
            "Commodity": "Scrap (mixed)",
            "Region": "Italy ex‑works",
            "Price_EUR": 320.0,
            "Price_USD": 320.0 * eur_usd,
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
            "Price_USD": 105.04,
            "Source": "https://fred.stlouisfed.org/series/PCOALAUUSDM",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Western Europe ex‑works",
            "Price_EUR": 545.0,
            "Price_USD": 545.0 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Italy ex‑works",
            "Price_EUR": 527.5,
            "Price_USD": 527.5 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "Southern Europe CIF",
            "Price_EUR": 500.0,
            "Price_USD": 500.0 * eur_usd,
            "Source": "https://gmk.center/en/news/global-prices-for-hot-rolled-coil-came-under-pressure-in-most-regions-in-july/",
        },
        {
            "Commodity": "HRC (Hot Rolled Coil)",
            "Region": "North America ex‑works",
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
    return pd.DataFrame(data)


# -----------------------------------------------------------------------------
# Kallanish Excel parsing
# -----------------------------------------------------------------------------

def parse_kallanish_workbook(path: str) -> Dict[str, pd.DataFrame]:
    """Parse a Kallanish Excel file into multiple price series.

    See streamlit_dashboard.py for full details.  Returns a mapping
    of product names to DataFrames with columns ``Date`` and ``Price``.
    """
    try:
        df = pd.read_excel(path, sheet_name="Price Series", header=None, engine="openpyxl")
    except Exception:
        return {}
    # Attempt to locate the row labelled 'Dates'
    try:
        dates_row = df[df[0] == "Dates"].index[0]
    except Exception:
        dates_row = 9
    start_idx = dates_row + 1
    product_row = dates_row - 1
    ncols = df.shape[1]
    col = 1
    products: Dict[str, pd.DataFrame] = {}
    while col + 2 < ncols:
        name = df.iat[product_row, col]
        if pd.isna(name):
            tmp_row = product_row
            while tmp_row >= 0 and pd.isna(name):
                tmp_row -= 1
                name = df.iat[tmp_row, col] if tmp_row >= 0 else ""
        name = str(name).strip() if name is not None else ""
        avg_col = col + 2
        data = df.iloc[start_idx:, [0, avg_col]].copy()
        data.columns = ["Date", "Price"]
        data = data.dropna(subset=["Date", "Price"])
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data["Price"] = pd.to_numeric(data["Price"], errors="coerce")
        data = data.dropna(subset=["Date", "Price"])
        if name:
            products[name] = data
        col += 3
    return products


def load_local_price_series(data_dir: str = "data") -> Dict[str, pd.DataFrame]:
    """Load all price series from .xlsx files in ``data_dir``."""
    series: Dict[str, pd.DataFrame] = {}
    for path in glob.glob(os.path.join(data_dir, "*.xlsx")):
        file_series = parse_kallanish_workbook(path)
        for name, df in file_series.items():
            if name in series:
                combined = pd.concat([series[name], df]).drop_duplicates(subset=["Date"], keep="last")
                series[name] = combined.sort_values("Date")
            else:
                series[name] = df.sort_values("Date")
    return series


def load_uploaded_series(files) -> Dict[str, pd.DataFrame]:
    """Load series from files uploaded via Streamlit's uploader."""
    series: Dict[str, pd.DataFrame] = {}
    if not files:
        return series
    for file in files:
        base_name = os.path.splitext(file.name)[0]
        try:
            file_series = parse_kallanish_workbook(file)
        except Exception:
            file_series = {}
        if not file_series:
            try:
                df = pd.read_excel(file, sheet_name="Price Series", engine="openpyxl", header=None)
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
        for name, df in file_series.items():
            if name in series:
                combined = pd.concat([series[name], df]).drop_duplicates(subset=["Date"], keep="last")
                series[name] = combined.sort_values("Date")
            else:
                series[name] = df.sort_values("Date")
    return series


# -----------------------------------------------------------------------------
# News headlines helper
# -----------------------------------------------------------------------------

def fetch_gmk_headlines(limit: int = 50) -> List[Tuple[str, str]]:
    """Retrieve (title, link) tuples from GMK Center's RSS feed."""
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
# Streamlit app
# -----------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Steel Market Dashboard", layout="wide")
    st.title("Steel Market Dashboard")

    # Sidebar: file upload and time range selection
    st.sidebar.header("Upload Kallanish .xlsx files (optional)")
    uploaded_files = st.sidebar.file_uploader(
        "Drag and drop files here", type=["xlsx"], accept_multiple_files=True
    )
    st.sidebar.markdown("---")
    # Time range selection for price charts
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

    # Exchange rate and table
    eur_usd, rate_date = fetch_exchange_rate()
    st.subheader("Exchange Rate")
    if rate_date:
        st.markdown(f"**1 EUR = {eur_usd:.4f} USD** (quoted {rate_date})")
    else:
        st.warning("Could not fetch exchange rate. Using fallback rate of 1.00.")
        st.markdown(f"**1 EUR = {eur_usd:.4f} USD**")

    # Exchange rate chart selection
    st.sidebar.markdown("### Exchange Rate Range")
    fx_ranges = {
        "7 Days": _dt.timedelta(days=7),
        "1 Month": _dt.timedelta(days=30),
        "3 Months": _dt.timedelta(days=90),
        "6 Months": _dt.timedelta(days=180),
        "1 Year": _dt.timedelta(days=365),
    }
    fx_label = st.sidebar.selectbox("Select time range for exchange rate", list(fx_ranges.keys()), index=0)
    fx_delta = fx_ranges[fx_label]
    fx_start = _dt.date.today() - fx_delta
    fx_end = _dt.date.today()
    fx_series = fetch_exchange_rate_series(fx_start, fx_end)
    st.markdown("#### EUR→USD Exchange Rate Trend")
    if fx_series is not None and not fx_series.empty:
        min_rate = fx_series["Rate"].min()
        max_rate = fx_series["Rate"].max()
        min_y = max(0.0, min_rate * 0.95)
        max_y = max_rate * 1.05
        rate_chart = (
            alt.Chart(fx_series)
            .mark_line()
            .encode(
                x=alt.X("Date:T", title="Date"),
                y=alt.Y("Rate:Q", scale=alt.Scale(domain=[min_y, max_y]), title="EUR→USD Rate"),
            )
            .properties(height=250)
        )
        st.altair_chart(rate_chart, use_container_width=True)
    else:
        st.info("Could not retrieve exchange rate history for the selected period.")

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
    latest_df_display["Source"] = latest_df_display["Source"].apply(lambda url: f"[link]({url})")
    st.write(
        "European HRC prices are shown in EUR/t and converted to USD using the current exchange rate."
    )
    st.dataframe(
        latest_df_display[["Commodity", "Region", "Price_EUR", "Price_USD", "Source"]],
        hide_index=True,
    )

    # Historical price trends: multi-series graphs
    st.subheader("Historical Price Trends")
    local_series = load_local_price_series("data")
    uploaded_series = load_uploaded_series(uploaded_files)
    all_series: Dict[str, pd.DataFrame] = local_series.copy()
    for name, df in uploaded_series.items():
        if name in all_series:
            combined = pd.concat([all_series[name], df]).drop_duplicates(subset=["Date"], keep="last")
            all_series[name] = combined.sort_values("Date")
        else:
            all_series[name] = df.sort_values("Date")
    if not all_series:
        st.info(
            "Upload Kallanish price files via the sidebar or place them in the `data/` folder of the repository to see price trends."
        )
    else:
        cutoff_dt = _dt.datetime.today() - selected_delta
        product_names = sorted(all_series.keys())
        st.sidebar.markdown("### Graph Filters")
        default_g1 = [p for p in product_names if "HRC" in p][:3]
        selected_g1 = st.sidebar.multiselect(
            "Select series for Graph 1",
            options=product_names,
            default=default_g1,
            key="graph1_select_v4",
        )
        selected_g2 = st.sidebar.multiselect(
            "Select series for Graph 2",
            options=product_names,
            default=[p for p in product_names if p not in default_g1][:3],
            key="graph2_select_v4",
        )
        def draw_multi_series(selected_list: List[str], title: str) -> None:
            st.markdown(f"#### {title}")
            if not selected_list:
                st.info("Select one or more series to display.")
                return
            chart_frames: List[pd.DataFrame] = []
            latest_labels: List[str] = []
            for series_name in selected_list:
                ser_df = all_series.get(series_name)
                if ser_df is None:
                    continue
                df_recent = ser_df[ser_df["Date"] >= cutoff_dt]
                if df_recent.empty:
                    continue
                tmp = df_recent.copy()
                tmp["Product"] = series_name
                chart_frames.append(tmp)
                # Determine latest entry from the full series (not just recent)
                latest_row = ser_df.iloc[-1]
                latest_labels.append(
                    f"{series_name}: {latest_row['Price']:.2f} ({latest_row['Date'].date()})"
                )
            if not chart_frames:
                st.info("No data available for selected series in this time range.")
                return
            combined = pd.concat(chart_frames, ignore_index=True)
            min_price = combined["Price"].min()
            max_price = combined["Price"].max()
            min_y = max(0.0, min_price * 0.8)
            max_y = max_price * 1.05
            st.markdown(", ".join(latest_labels))
            line_chart = (
                alt.Chart(combined)
                .mark_line()
                .encode(
                    x=alt.X("Date:T", title="Date"),
                    y=alt.Y("Price:Q", scale=alt.Scale(domain=[min_y, max_y]), title="Price"),
                    color=alt.Color("Product:N", legend=alt.Legend(title="Series")),
                )
                .properties(height=300)
            )
            st.altair_chart(line_chart, use_container_width=True)
        # Draw Graphs 1 and 2
        draw_multi_series(selected_g1, "Graph 1")
        draw_multi_series(selected_g2, "Graph 2")

    # News headlines
    st.subheader("Steel Industry Headlines")
    headlines = fetch_gmk_headlines(limit=50)
    if 'removed_headlines_v4' not in st.session_state:
        st.session_state['removed_headlines_v4'] = set()
    available = [h for h in headlines if h[1] not in st.session_state['removed_headlines_v4']]
    display_count = 20
    to_display = available[:display_count]
    if not to_display:
        st.info("No headlines to display.")
    else:
        for title, link in to_display:
            cols = st.columns([20, 1])
            with cols[0]:
                st.markdown(f"- [{title}]({link})")
            with cols[1]:
                if st.button("✖", key=f"del_{link}_v4"):
                    st.session_state['removed_headlines_v4'].add(link)
                    st.experimental_rerun()

    # Footer
    st.markdown("---")
    st.write("### Upcoming Features:")
    st.write("- Live sync with Google Sheets")
    st.write("- News integration from SteelOrbis, Shanghai Metals Market and Kallanish")
    st.write("- Mobile‑friendly manual price input form")


if __name__ == "__main__":
    main()