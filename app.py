"""
StockPilot – Bestands- & Verkaufs-Dashboard
-------------------------------------------
Selbstbedienbares Web-Tool: Kunde lädt seine eigene Verkaufs-/Bestandsdatei
(CSV oder Excel) hoch und bekommt sofort ein interaktives Dashboard —
ohne Excel-Kenntnisse, ohne Support-Anruf.
"""

import io
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # ohne Display-Server (für Streamlit Cloud)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
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
        /* Akzentfarbe (Tabs, Slider, Checkbox, Radio, Links) kommt aus
           .streamlit/config.toml (primaryColor). Hier nur die Custom-Elemente. */
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


def _eur(x) -> str:
    """Zahl im deutschen Euro-Format (1.234,56 €)."""
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def build_pdf_report(daily, top, abc_counts, kpis, period_label, brand):
    """Baut einen gebrandeten einseitigen PDF-Report (KPIs, Umsatztrend,
    Top-Artikel, ABC-Zusammenfassung) und gibt ihn als Bytes zurück."""
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        fig = plt.figure(figsize=(11.69, 8.27))  # A4 quer
        fig.suptitle("StockPilot – Bestands- & Verkaufsreport", x=0.06, y=0.96,
                     ha="left", fontsize=20, fontstyle="italic", fontweight="bold",
                     color="#111827")
        fig.text(0.06, 0.915, f"Zeitraum: {period_label}", ha="left",
                 fontsize=10, color="#64748b")
        fig.text(0.06, 0.895, f"Erstellt am {datetime.today():%d.%m.%Y}", ha="left",
                 fontsize=9, color="#94a3b8")

        # KPI-Zeile als Text
        kpi_x = [0.06, 0.30, 0.54, 0.78]
        for x, (label, value) in zip(kpi_x, kpis):
            fig.text(x, 0.83, value, ha="left", fontsize=17, fontweight="bold",
                     fontstyle="italic", color=brand)
            fig.text(x, 0.80, label, ha="left", fontsize=9, color="#64748b")

        # Umsatztrend
        ax1 = fig.add_axes([0.06, 0.40, 0.88, 0.32])
        ax1.plot(daily["Datum"], daily["Umsatz"], color=brand, linewidth=1.2, label="Umsatz")
        if "Gleitender Ø" in daily:
            ax1.plot(daily["Datum"], daily["Gleitender Ø"], color="#5eead4",
                     linewidth=2, label="Gleitender Ø")
        ax1.set_title("Umsatztrend", loc="left", fontsize=12, fontweight="bold", color="#111827")
        ax1.legend(loc="upper right", fontsize=8, frameon=False)
        ax1.spines[["top", "right"]].set_visible(False)
        ax1.tick_params(labelsize=8)

        # Top-Artikel
        ax2 = fig.add_axes([0.06, 0.06, 0.52, 0.26])
        ax2.barh(top["Artikel"][::-1], top["Umsatz"][::-1], color=brand)
        ax2.set_title("Top-Artikel nach Umsatz", loc="left", fontsize=12,
                      fontweight="bold", color="#111827")
        ax2.spines[["top", "right"]].set_visible(False)
        ax2.tick_params(labelsize=8)

        # ABC-Zusammenfassung
        fig.text(0.64, 0.30, "ABC-Analyse", fontsize=12, fontweight="bold", color="#111827")
        abc_lines = [
            f"A-Artikel (Top-Umsatz):  {abc_counts.get('A', 0)}",
            f"B-Artikel (Mittelfeld):  {abc_counts.get('B', 0)}",
            f"C-Artikel (Ausläufer):   {abc_counts.get('C', 0)}",
        ]
        for i, line in enumerate(abc_lines):
            fig.text(0.64, 0.25 - i * 0.035, line, fontsize=10, color="#334155")
        fig.text(0.64, 0.09, "StockPilot · getstockpilot.streamlit.app",
                 fontsize=8, color="#94a3b8")

        pdf.savefig(fig)
        plt.close(fig)
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
    start_d, end_d = min_d, max_d
    st.sidebar.caption(f"Zeitraum: {min_d:%d.%m.%Y}")
else:
    preset = st.sidebar.radio(
        "Zeitraum",
        ["Gesamter Zeitraum", "Letzte 30 Tage", "Letzte 90 Tage", "Benutzerdefiniert"],
    )
    if preset == "Letzte 30 Tage":
        default_start = max(min_d, max_d - timedelta(days=29))
    elif preset == "Letzte 90 Tage":
        default_start = max(min_d, max_d - timedelta(days=89))
    else:
        default_start = min_d

    picked = st.sidebar.date_input(
        "Von – Bis",
        value=(default_start, max_d),
        min_value=min_d,
        max_value=max_d,
        format="DD.MM.YYYY",
        disabled=(preset != "Benutzerdefiniert"),
        key=f"daterange_{preset}",
        help="Bei 'Benutzerdefiniert' Start- und Enddatum frei im Kalender wählen.",
    )
    if isinstance(picked, (list, tuple)) and len(picked) == 2:
        start_d, end_d = picked
    elif isinstance(picked, (list, tuple)) and len(picked) == 1:
        start_d, end_d = picked[0], max_d
    else:
        start_d, end_d = default_start, max_d

all_products = sorted(df[product_col].dropna().astype(str).unique().tolist())
sel_products = st.sidebar.multiselect(
    "Artikel (leer = alle)", options=all_products, default=[]
)

st.sidebar.caption(f"Gewählt: {start_d:%d.%m.%Y} – {end_d:%d.%m.%Y}")
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
st.subheader("Report & Export")

period_label = f"{start_d:%d.%m.%Y} – {end_d:%d.%m.%Y}"
pdf_kpis = [
    ("Gesamtumsatz", _eur(total_revenue)),
    ("Verkaufte Menge", f"{total_qty:,.0f}".replace(",", ".")),
    ("Anzahl Artikel", f"{n_products}"),
    ("Ø Umsatz/Zeile", _eur(avg_row)),
]
top_pdf = by_product.head(10).rename(columns={product_col: "Artikel", revenue_col: "Umsatz"})
pdf_bytes = build_pdf_report(trend, top_pdf, counts, pdf_kpis, period_label, BRAND)

export_cols = st.columns(3)
with export_cols[0]:
    st.download_button(
        "📑 PDF-Report",
        data=pdf_bytes,
        file_name=f"stockpilot_report_{datetime.today():%Y-%m-%d}.pdf",
        mime="application/pdf",
        help="Fertiger, gebrandeter Report zum Weitergeben – KPIs, Umsatztrend, Top-Artikel, ABC.",
    )
with export_cols[1]:
    st.download_button(
        "⬇️ Auswertung als Excel",
        data=to_excel_bytes(dff),
        file_name=f"stockpilot_auswertung_{datetime.today():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with export_cols[2]:
    st.download_button(
        "⬇️ Artikel-Umsätze als Excel",
        data=to_excel_bytes(by_product.rename(columns={product_col: "Artikel", revenue_col: "Umsatz"})),
        file_name=f"stockpilot_artikel_{datetime.today():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with st.expander("📄 Gefilterte Rohdaten anzeigen"):
    st.dataframe(dff, use_container_width=True, hide_index=True)
