"""
StockPilot – Bestands- & Verkaufs-Dashboard
-------------------------------------------
Selbstbedienbares Web-Tool: Kunde lädt seine eigene Verkaufs-/Bestandsdatei
(CSV oder Excel) hoch und bekommt sofort ein interaktives Dashboard —
ohne Excel-Kenntnisse, ohne Support-Anruf.
"""

import io
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="StockPilot – Bestands- & Verkaufs-Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Markenfarben & Styling (theme-sicher: nutzt Streamlits CSS-Variablen,
#     damit es in Hell- UND Dunkelmodus funktioniert) ---
BRAND = "#0d9488"        # Petrol/Teal – StockPilot-Markenfarbe
BRAND_LIGHT = "#5eead4"  # heller Ton für Sekundär-Linien (z. B. gleitender Ø)

st.markdown(
    f"""
    <style>
        /* Markenfarbe per CSS (statt config.toml), damit die App weiterhin
           dem Hell/Dunkel-Theme des Betrachters folgt. */
        :root, .stApp {{ --primary-color: {BRAND} !important; }}
        [data-baseweb="tab-highlight"] {{ background-color: {BRAND} !important; }}
        .stSlider [data-baseweb="slider"] div[role="slider"] {{ background-color: {BRAND} !important; }}
        a, a:visited {{ color: {BRAND}; }}
        /* Kopfbereich im Altware-Stil: kursiv, fett, mit Feature-Breadcrumb */
        .sp-header {{ margin: 0 0 6px 0; }}
        .sp-title {{
            font-size: 2.4rem; font-weight: 800; font-style: italic;
            letter-spacing: -0.02em; line-height: 1.1;
        }}
        .sp-crumb {{
            margin-top: 6px; font-weight: 700; font-size: 0.9rem;
            opacity: 0.7;
        }}
        .sp-crumb b {{ color: {BRAND}; }}
        .sp-pill {{
            display: inline-block; background: {BRAND}; color: #fff;
            border-radius: 999px; padding: 2px 10px; margin-left: 8px;
            font-size: 0.72rem; font-weight: 800; vertical-align: middle;
        }}
        /* KPI-Karten mit Marken-Akzentlinie und kursiven Zahlen */
        div[data-testid="stMetric"] {{
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-top: 3px solid {BRAND};
            border-radius: 12px;
            padding: 14px 16px;
        }}
        div[data-testid="stMetricValue"] {{
            font-weight: 800; font-style: italic; font-size: 1.7rem;
        }}
        /* Buttons/Downloads in Markenfarbe */
        .stDownloadButton button, .stButton button {{
            border-color: {BRAND};
        }}
        .stDownloadButton button:hover, .stButton button:hover {{
            background: {BRAND}; color: #fff; border-color: {BRAND};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sp-header">
        <div class="sp-title">📊 StockPilot</div>
        <div class="sp-crumb">Import <b>·</b> Filter <b>·</b> KPIs <b>·</b> ABC-Analyse <b>·</b> Export
            <span class="sp-pill">LIVE</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    "Dein Bestands- & Verkaufs-Dashboard: Datei hochladen, in wenigen Sekunden "
    "ein fertiges Dashboard erhalten — ganz ohne Excel-Formeln oder manuelle Auswertung."
)


# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------
def generate_demo_data() -> pd.DataFrame:
    """Realistische Demo-Daten (fiktive Bäckerei), damit Interessenten das Tool
    ausprobieren können, bevor sie eigene Daten hochladen."""
    rng = np.random.default_rng(42)
    products = [
        "Brot Roggen", "Brötchen Mehrkorn", "Croissant", "Stollen",
        "Baguette", "Vollkornbrot", "Zopf", "Laugenbrezel",
    ]
    dates = pd.date_range(end=datetime.today(), periods=120)
    rows = []
    for d in dates:
        for p in products:
            base = rng.integers(5, 40)
            menge = max(0, int(base + rng.normal(0, 5)))
            preis = round(rng.uniform(1.5, 6.5), 2)
            bestand = max(0, int(rng.normal(50, 20)))
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


def _read_csv_robust(raw: bytes) -> pd.DataFrame:
    """Liest CSV-Dateien robust ein — erkennt Encoding, Trennzeichen (Semikolon
    bei deutschen Exporten) und Dezimalzeichen (Komma) automatisch."""
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("utf-8", errors="replace")

    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    sep = ";" if first_line.count(";") >= first_line.count(",") else ","
    if sep == ";":  # deutsches Format: Komma-Dezimal, Tausenderpunkt
        return pd.read_csv(io.StringIO(text), sep=sep, decimal=",", thousands=".")
    return pd.read_csv(io.StringIO(text), sep=sep)


def load_uploaded(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return _read_csv_robust(file.getvalue())
    return pd.read_excel(file)


def to_numeric_de(series: pd.Series) -> pd.Series:
    """Wandelt eine Spalte sicher in Zahlen um — auch wenn Zahlen im deutschen
    Format als Text ankamen (z. B. '1.234,56')."""
    if pd.api.types.is_numeric_dtype(series):
        return series
    s = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)   # Tausenderpunkte raus
        .str.replace(",", ".", regex=False)  # Komma -> Dezimalpunkt
        .str.replace(r"[^0-9.\-]", "", regex=True)
    )
    return pd.to_numeric(s, errors="coerce")


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Auswertung") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


# --- Sidebar: Datenquelle ---
with st.sidebar:
    st.header("1. Daten")
    use_demo = st.checkbox("Demo-Daten verwenden", value=True)
    uploaded_file = None
    if not use_demo:
        uploaded_file = st.file_uploader(
            "CSV- oder Excel-Datei hochladen", type=["csv", "xlsx", "xls"]
        )
    st.download_button(
        "📄 Beispiel-Vorlage (Excel)",
        data=to_excel_bytes(generate_demo_data().head(40)),
        file_name="stockpilot_vorlage.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Lade dir eine Beispieldatei herunter, um das erwartete Format zu sehen.",
    )

if use_demo:
    df = generate_demo_data()
    st.info(
        "Du siehst gerade Demo-Daten einer fiktiven Bäckerei. "
        "Lade in der Seitenleiste deine eigene Datei hoch, um dein eigenes Dashboard zu sehen."
    )
elif uploaded_file:
    try:
        df = load_uploaded(uploaded_file)
    except Exception as e:  # noqa: BLE001 – dem Nutzer eine klare Meldung zeigen
        st.error(f"Datei konnte nicht gelesen werden: {e}")
        st.stop()
else:
    st.warning("Bitte lade eine Datei hoch oder aktiviere die Demo-Daten in der Seitenleiste.")
    st.stop()


# ---------------------------------------------------------------------------
# Spalten-Zuordnung
# ---------------------------------------------------------------------------
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
df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
if df[date_col].isna().all():
    st.error("Die Datum-Spalte konnte nicht als Datum erkannt werden. Bitte prüfe die Zuordnung links.")
    st.stop()

df[qty_col] = to_numeric_de(df[qty_col])
df[revenue_col] = to_numeric_de(df[revenue_col])
if stock_col != "(keine)":
    df[stock_col] = to_numeric_de(df[stock_col])

n_dropped = int(df[date_col].isna().sum())
df = df.dropna(subset=[date_col]).sort_values(date_col)
if n_dropped:
    st.caption(f"Hinweis: {n_dropped} Zeile(n) ohne gültiges Datum wurden ausgeblendet.")


# ---------------------------------------------------------------------------
# 3. Filter
# ---------------------------------------------------------------------------
st.sidebar.header("3. Filter")
min_d, max_d = df[date_col].min().date(), df[date_col].max().date()
if min_d == max_d:
    date_range = (min_d, max_d)
    st.sidebar.caption(f"Zeitraum: {min_d:%d.%m.%Y}")
else:
    date_range = st.sidebar.slider(
        "Zeitraum", min_value=min_d, max_value=max_d, value=(min_d, max_d), format="DD.MM.YYYY"
    )

all_products = sorted(df[product_col].dropna().astype(str).unique().tolist())
sel_products = st.sidebar.multiselect(
    "Artikel (leer = alle)", options=all_products, default=[]
)

start_d, end_d = date_range
mask = (df[date_col].dt.date >= start_d) & (df[date_col].dt.date <= end_d)
if sel_products:
    mask &= df[product_col].astype(str).isin(sel_products)
dff = df[mask].copy()

if dff.empty:
    st.warning("Für die gewählten Filter gibt es keine Daten. Bitte Filter anpassen.")
    st.stop()


# ---------------------------------------------------------------------------
# KPIs mit Perioden-Vergleich
# ---------------------------------------------------------------------------
def previous_period_value(column, agg="sum"):
    """Wert derselben Kennzahl in der gleich langen Periode direkt davor
    (für Delta-Anzeige). Gibt None zurück, wenn keine Vorperiode existiert."""
    length = (end_d - start_d) + timedelta(days=1)
    prev_start = start_d - length
    prev_end = start_d - timedelta(days=1)
    prev_mask = (df[date_col].dt.date >= prev_start) & (df[date_col].dt.date <= prev_end)
    if sel_products:
        prev_mask &= df[product_col].astype(str).isin(sel_products)
    prev = df[prev_mask]
    if prev.empty:
        return None
    return prev[column].agg(agg)


def delta_str(current, previous):
    if previous is None or previous == 0:
        return None
    pct = (current - previous) / previous * 100
    return f"{pct:+.1f}%"


total_revenue = dff[revenue_col].sum()
total_qty = dff[qty_col].sum()
n_products = dff[product_col].nunique()
avg_row = total_revenue / len(dff) if len(dff) else 0

prev_rev = previous_period_value(revenue_col, "sum")
prev_qty = previous_period_value(qty_col, "sum")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Gesamtumsatz", f"{total_revenue:,.2f} €", delta=delta_str(total_revenue, prev_rev))
k2.metric("Verkaufte Menge", f"{total_qty:,.0f}", delta=delta_str(total_qty, prev_qty))
k3.metric("Anzahl Artikel", f"{n_products}")
k4.metric("Ø Umsatz/Zeile", f"{avg_row:,.2f} €")
if prev_rev is not None:
    st.caption("Delta = Vergleich zur gleich langen Periode direkt davor.")

st.divider()


# ---------------------------------------------------------------------------
# Tabs: Übersicht / Artikel / Bestand
# ---------------------------------------------------------------------------
tab_labels = ["📈 Übersicht", "📦 Artikel"]
has_stock = stock_col != "(keine)"
if has_stock:
    tab_labels.append("🏷️ Bestand")
tabs = st.tabs(tab_labels)

# --- Übersicht ---
with tabs[0]:
    st.subheader("Umsatztrend")
    trend = dff.groupby(dff[date_col].dt.date)[revenue_col].sum().reset_index()
    trend.columns = ["Datum", "Umsatz"]
    trend["Datum"] = pd.to_datetime(trend["Datum"])
    window = min(7, max(2, len(trend) // 4))
    trend["Gleitender Ø"] = trend["Umsatz"].rolling(window, min_periods=1).mean()
    fig_trend = px.line(
        trend, x="Datum", y=["Umsatz", "Gleitender Ø"],
        labels={"value": "Umsatz (€)", "variable": ""},
        color_discrete_sequence=[BRAND, BRAND_LIGHT],
    )
    fig_trend.update_layout(margin=dict(t=10), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_trend, use_container_width=True)
    st.caption(f"Gleitender Durchschnitt über {window} Tage – glättet Ausreißer und zeigt den Trend.")

# --- Artikel ---
with tabs[1]:
    by_product = (
        dff.groupby(product_col)[revenue_col].sum().sort_values(ascending=False).reset_index()
    )
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Top 10 nach Umsatz")
        top = by_product.head(10)
        fig_top = px.bar(
            top, x=revenue_col, y=product_col, orientation="h",
            labels={revenue_col: "Umsatz (€)", product_col: "Artikel"},
            color_discrete_sequence=[BRAND],
        )
        fig_top.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=10))
        st.plotly_chart(fig_top, use_container_width=True)
    with col_right:
        st.subheader("Flop 10 nach Umsatz")
        flop = by_product.tail(10).sort_values(revenue_col)
        fig_flop = px.bar(
            flop, x=revenue_col, y=product_col, orientation="h",
            labels={revenue_col: "Umsatz (€)", product_col: "Artikel"},
            color_discrete_sequence=[BRAND_LIGHT],
        )
        fig_flop.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=10))
        st.plotly_chart(fig_flop, use_container_width=True)

    st.divider()
    st.subheader("ABC-Analyse")
    abc = by_product.copy()
    abc["Umsatzanteil %"] = abc[revenue_col] / abc[revenue_col].sum() * 100
    abc["Kumuliert %"] = abc["Umsatzanteil %"].cumsum()
    abc["Klasse"] = np.where(
        abc["Kumuliert %"] <= 80, "A",
        np.where(abc["Kumuliert %"] <= 95, "B", "C"),
    )
    counts = abc["Klasse"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("A-Artikel (Top-Umsatz)", int(counts.get("A", 0)))
    c2.metric("B-Artikel (Mittelfeld)", int(counts.get("B", 0)))
    c3.metric("C-Artikel (Ausläufer)", int(counts.get("C", 0)))
    abc_show = abc.rename(columns={product_col: "Artikel", revenue_col: "Umsatz"})
    abc_show["Umsatz"] = abc_show["Umsatz"].round(2)
    abc_show["Umsatzanteil %"] = abc_show["Umsatzanteil %"].round(1)
    abc_show["Kumuliert %"] = abc_show["Kumuliert %"].round(1)
    st.dataframe(abc_show, use_container_width=True, hide_index=True)
    st.caption("A = ca. 80 % des Umsatzes, B = nächste 15 %, C = der Rest. Zeigt, worauf es sich zu konzentrieren lohnt.")

# --- Bestand ---
if has_stock:
    with tabs[2]:
        st.subheader("Bestandsübersicht (aktuellster Stand je Artikel)")
        latest = dff.sort_values(date_col).groupby(product_col).tail(1)
        fig_stock = px.bar(
            latest.sort_values(stock_col), x=stock_col, y=product_col, orientation="h",
            labels={stock_col: "Bestand", product_col: "Artikel"},
            color_discrete_sequence=[BRAND],
        )
        fig_stock.update_layout(margin=dict(t=10))
        st.plotly_chart(fig_stock, use_container_width=True)

        threshold = latest[stock_col].quantile(0.2)
        low_stock = latest[latest[stock_col] < threshold]
        if len(low_stock):
            st.warning(
                f"🔴 {len(low_stock)} Artikel mit niedrigem Bestand (unterste 20 %): "
                + ", ".join(low_stock[product_col].astype(str).tolist())
            )
        else:
            st.success("🟢 Kein Artikel im kritischen Bestandsbereich.")


# ---------------------------------------------------------------------------
# Export & Rohdaten
# ---------------------------------------------------------------------------
st.divider()
export_cols = st.columns(2)
with export_cols[0]:
    st.download_button(
        "⬇️ Auswertung als Excel",
        data=to_excel_bytes(dff),
        file_name=f"stockpilot_auswertung_{datetime.today():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with export_cols[1]:
    st.download_button(
        "⬇️ Artikel-Umsätze als Excel",
        data=to_excel_bytes(by_product.rename(columns={product_col: "Artikel", revenue_col: "Umsatz"})),
        file_name=f"stockpilot_artikel_{datetime.today():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with st.expander("📄 Gefilterte Rohdaten anzeigen"):
    st.dataframe(dff, use_container_width=True, hide_index=True)
