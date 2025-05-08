# 🧠 AI Agent Prompt: Plane.so Deployment Tool Builder

api reference here: https://developers.plane.so/api-reference/introduction

## 🎯 Ziel

Erstelle ein **Python-basiertes CLI-Tool**, das aus einer JSON-Datei automatisch **Module und zugehörige Issues** in einem Projekt auf [Plane.so](https://plane.so) erstellt.

---

## 📥 Input

### 1. JSON-Datei (Work Breakdown Structure)

```json
{
  "WP1 – User Management": [
    "Sign-up/Login mit JWT + TOTP",
    "Sign-out / Token Refresh",
    "Passwort-Reset via E-Mail"
  ],
  "WP2 – MDM": [
    "Entitätsdefinitionen",
    "CRUD-APIs",
    "UI-Komponenten"
  ]
}

PLANE_API_KEY=your-api-key
PLANE_WORKSPACE_SLUG=your-workspace-slug
PLANE_PROJECT_ID=your-project-id
PLANE_HOST=https://api.plane.so

⚙️ Funktionalität
	1.	Module erstellen
Jeder oberste Schlüssel der JSON-Struktur wird als Modul angelegt.
	2.	Issues erstellen
Jede Aufgabe innerhalb eines Moduls wird als Issue erstellt.
	3.	Zuordnung der Issues zum Modul
Jedes Issue wird dem richtigen Modul per API zugewiesen.

💻 Technische Anforderungen
	•	Sprache: Python ≥ 3.9
	•	Pakete: requests, python-dotenv
	•	Ausführung:

python main.py --input work_packages.json

Optionaler Flag:
	•	--dry-run: führt keine API-Calls aus, nur Simulation

🔗 Verwendete Plane.so API-Endpunkte
Aktion
Endpoint
Modul erstellen
POST /modules/
Issue erstellen
POST /issues/
Issues einem Modul zuweisen
POST /modules/{module_id}/module-issues/

🧩 Zusatzfeatures
	•	Fehlertoleranz: bei Fehlern keine Unterbrechung, Logging auf Konsole
	•	Ergebnisübersicht: Ausgabe aller erstellten Module und Issues am Ende
	•	Optional ausbaufähig: Logging in Datei, Markdown-Export, Mapping-Tabelle

👤 Zielgruppe

Interne Entwickler:innen oder KI-Agenten, die strukturierte Projektpläne automatisiert in Plane.so abbilden wollen – für eine standardisierte, wiederverwendbare Projektvorbereitung.
