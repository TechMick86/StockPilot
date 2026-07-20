# StockPilot – Bestands- & Verkaufs-Dashboard

Selbstbedienbares Web-Tool: Kunde lädt seine Verkaufs-/Bestandsdatei (CSV oder Excel)
hoch und erhält sofort ein interaktives Dashboard – ganz ohne Excel-Kenntnisse und
ohne dass du persönlich involviert sein musst.

Enthält Demo-Daten (fiktive Bäckerei), damit Interessenten das Tool direkt
ausprobieren können, bevor sie eigene Daten hochladen.

**Live:** https://getstockpilot.streamlit.app

## Funktionen

- **Robuster Import:** CSV (auch deutsches Format mit Semikolon, Komma-Dezimal, Tausenderpunkt und Umlauten) und Excel.
- **Automatische Spaltenerkennung** mit manueller Korrektur — funktioniert mit jeder Kundendatei.
- **Filter:** Zeitraum-Slider und Artikel-Auswahl.
- **KPIs mit Perioden-Vergleich** (Delta zur gleich langen Vorperiode).
- **Tabs:** Übersicht (Umsatztrend + gleitender Durchschnitt), Artikel (Top/Flop 10 + ABC-Analyse), Bestand (Übersicht + Niedrigbestand-Warnung).
- **Export:** aufbereitete Auswertung und Artikel-Umsätze als Excel, Beispiel-Vorlage zum Download.
- **Hell- und Dunkelmodus** (folgt dem Theme des Betrachters).
