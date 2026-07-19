"""
Bestands- & Verkaufs-Dashboard-Generator
------------------------------------------
Selbstbedienbares Web-Tool: Kunde lädt seine eigene Verkaufs-/Bestandsdatei
(CSV oder Excel) hoch und bekommt sofort ein interaktives Dashboard —
ohne Excel-Kenntnisse, ohne Support-Anruf.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Bestands- & Verkaufs-Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Styling ---
st.markdown(
    """
    <style>
        div[data-testid="metric-container"] {
            background-color: white;
            border: 1px solid #e6e6e6;
            border-radius: 10px;
            padding: 16px;
        }
        h1, h2, h3 { color: #1a1a2e; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Bestands- & Verkaufs-Dashboard")
st.caption(
    "Datei hochladen, in wenigen Sekunden ein fertiges Dashboard erhalten — "
    "ganz ohne Excel-Formeln oder manuelle Auswertung."
)

# --- Sidebar: Datenquelle ---
with st.sidebar:
    st.header("1. Daten")
    use_demo = st.checkbox("Demo-Daten verwenden", value=True)
    uploaded_file = None
    if not use_demo:
        uploaded_file = st.file_uploader(
            "CSV- oder Excel-Datei hochladen", type=["csv", "xlsx", "xls"]
        )


def generate_demo_data() -> pd.DataFrame:
    """Erzeugt realistische Demo-Daten (fiktive Bäckerei), damit Interessenten
    das Tool ausprobieren können, bevor sie eigene Daten hochladen."""
    np.random.seed(42)
    products = [
        "Brot Roggen", "Brötchen Mehrkorn", "Croissant", "Stollen",
        "Baguette", "Vollkornbrot", "Zopf", "Laugenbrezel",
    ]
    dates = pd.date_range(end=datetime.today(), periods=90)
    rows = []
    for d in dates:
        for p in products:
            base = np.random.randint(5, 40)
            menge = max(0, int(base + np.random.normal(0, 5)))
            preis = round(np.random.uniform(1.5, 6.5), 2)
            bestand = max(0, int(np.random.normal(50, 20)))
            rows.append(
                {
                    "Datum": d,
                    "Artikel": p,
                    "Menge": menge,
                    "Umsatz": round(menge * preis, 2),
                    "Bestand": bestand,
                }
            )
    return pd.DataFrame(rows)


def load_uploaded(file) -> pd.DataFrame:
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


# --- Daten laden ---
if use_demo:
    df = generate_demo_data()
    st.info(
        "Du siehst gerade Demo-Daten einer fiktiven Bäckerei. "
        "Lade in der Seitenleiste deine eigene Datei hoch, um dein eigenes Dashboard zu sehen."
    )
elif uploaded_file:
    try:
        df = load_uploaded(uploaded_file)
    except Exception as e:
        st.error(f"Datei konnte nicht gelesen werden: {e}")
        st.stop()
else:
    st.warning("Bitte lade eine Datei hoch oder aktiviere die Demo-Daten in der Seitenleiste.")
    st.stop()

# --- Spalten-Zuordnung (Daten sehen bei jedem Kunden anders aus) ---
st.sidebar.header("2. Spalten zuordnen")
cols = df.columns.tolist()


def guess_col(keywords, default_index=0):
    for i, c in enumerate(cols):
        if any(k in str(c).lower() for k in keywords):
            return i
    return default_index


date_col = st.sidebar.selectbox("Datum-Spalte", cols, index=guess_col(["datum", "date"]))
product_col = st.sidebar.selectbox("Artikel-Spalte", cols, index=guess_col(["artikel", "produkt", "product"]))
qty_col = st.sidebar.selectbox("Menge-Spalte", cols, index=guess_col(["menge", "anzahl", "qty"]))
revenue_col = st.sidebar.selectbox("Umsatz-Spalte", cols, index=guess_col(["umsatz", "revenue", "betrag"]))
stock_col_options = ["(keine)"] + cols
stock_col = st.sidebar.selectbox(
    "Bestand-Spalte (optional)",
    stock_col_options,
    index=(cols.index("Bestand") + 1 if "Bestand" in cols else 0),
)

# --- Datenaufbereitung ---
try:
    df[date_col] = pd.to_datetime(df[date_col])
except Exception:
    st.error("Die Datum-Spalte konnte nicht als Datum erkannt werden. Bitte prüfe die Zuordnung links.")
    st.stop()

# --- KPI-Kacheln ---
total_revenue = df[revenue_col].sum()
total_qty = df[qty_col].sum()
n_products = df[product_col].nunique()
avg_row = total_revenue / len(df) if len(df) else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Gesamtumsatz", f"{total_revenue:,.2f} €")
k2.metric("Verkaufte Menge", f"{total_qty:,.0f}")
k3.metric("Anzahl Artikel", f"{n_products}")
k4.metric("Ø Umsatz/Zeile", f"{avg_row:,.2f} €")

st.divider()

# --- Umsatztrend ---
st.subheader("Umsatztrend")
trend = df.groupby(date_col)[revenue_col].sum().reset_index()
fig_trend = px.line(trend, x=date_col, y=revenue_col, labels={date_col: "Datum", revenue_col: "Umsatz (€)"})
fig_trend.update_layout(margin=dict(t=10))
st.plotly_chart(fig_trend, use_container_width=True)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top 10 Artikel nach Umsatz")
    top = df.groupby(product_col)[revenue_col].sum().sort_values(ascending=False).head(10).reset_index()
    fig_top = px.bar(
        top, x=revenue_col, y=product_col, orientation="h",
        labels={revenue_col: "Umsatz (€)", product_col: "Artikel"},
    )
    fig_top.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=10))
    st.plotly_chart(fig_top, use_container_width=True)

with col_right:
    st.subheader("Flop 10 Artikel nach Umsatz")
    flop = df.groupby(product_col)[revenue_col].sum().sort_values(ascending=True).head(10).reset_index()
    fig_flop = px.bar(
        flop, x=revenue_col, y=product_col, orientation="h",
        labels={revenue_col: "Umsatz (€)", product_col: "Artikel"},
    )
    fig_flop.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=10))
    st.plotly_chart(fig_flop, use_container_width=True)

# --- Bestand (optional) ---
if stock_col != "(keine)":
    st.divider()
    st.subheader("Bestandsübersicht (aktuellster Stand je Artikel)")
    latest = df.sort_values(date_col).groupby(product_col).tail(1)
    fig_stock = px.bar(
        latest.sort_values(stock_col), x=stock_col, y=product_col, orientation="h",
        labels={stock_col: "Bestand", product_col: "Artikel"},
    )
    st.plotly_chart(fig_stock, use_container_width=True)

    low_stock = latest[latest[stock_col] < latest[stock_col].quantile(0.2)]
    if len(low_stock):
        st.warning(
            f"{len(low_stock)} Artikel mit niedrigem Bestand (unterste 20%): "
            + ", ".join(low_stock[product_col].astype(str).tolist())
        )

st.divider()
with st.expander("📄 Rohdaten anzeigen"):
    st.dataframe(df, use_container_width=True)
