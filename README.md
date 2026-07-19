# Bestands- & Verkaufs-Dashboard-Generator

Selbstbedienbares Web-Tool: Kunde lädt seine Verkaufs-/Bestandsdatei (CSV oder Excel)
hoch und erhält sofort ein interaktives Dashboard – ganz ohne Excel-Kenntnisse und
ohne dass du persönlich involviert sein musst.

Enthält Demo-Daten (fiktive Bäckerei), damit Interessenten das Tool direkt
ausprobieren können, bevor sie eigene Daten hochladen.

---

## 1. Lokal starten (zum Testen)

```bash
# Einmalig: virtuelle Umgebung anlegen
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# App starten
streamlit run app.py
```

Browser öffnet sich automatisch unter `http://localhost:8501`.

---

## 2. Kostenlos online stellen (Streamlit Community Cloud)

1. Projekt in ein GitHub-Repository laden (öffentlich oder privat)
2. Auf [share.streamlit.io](https://share.streamlit.io) mit GitHub-Account einloggen
3. "New app" → Repository auswählen → `app.py` als Hauptdatei angeben → Deploy
4. Du bekommst einen Link wie `https://dein-app-name.streamlit.app` – den kannst du
   direkt als Produkt-Link auf Malt.de/freelance.de oder in Angeboten verwenden

Kostenlos für öffentliche Apps. Für private/eigene Domain gibt es kostenpflichtige Optionen,
falls das später relevant wird.

---

## 3. Anpassungsideen für den Verkauf

- **Branding:** Titel, Farben und Logo in `app.py` (Bereich "Styling") an dein eigenes
  Branding anpassen, sobald du dich entschieden hast, wie du extern auftreten willst
- **Spalten-Zuordnung:** Das Tool erkennt automatisch typische Spaltennamen
  (z. B. "Datum", "Umsatz"), lässt sich aber für jede Kundendatei manuell zuordnen –
  das ist der Kern, warum es mit unterschiedlichen Kunden-Exporten funktioniert
- **Erweiterungsideen für später:** PDF-Export des Dashboards, Login/Zugangsbeschränkung
  für ein Abo-Modell, Mehrsprachigkeit

---

## 4. Was als Nächstes sinnvoll ist

1. Mit eigenen/anonymisierten Testdaten ausprobieren
2. Feedback von 1-2 Personen aus deinem Umfeld einholen (Verständlichkeit, nicht Verkauf)
3. Auf Streamlit Community Cloud deployen
4. Link in dein Malt.de/freelance.de-Profil einbauen
