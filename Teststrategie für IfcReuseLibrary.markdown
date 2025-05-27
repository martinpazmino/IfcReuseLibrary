# Teststrategie für IfcReuseLibrary

Um die Qualität und Funktionalität der Website des Projekts `IfcReuseLibrary` (https://github.com/martinpazmino/IfcReuseLibrary) sicherzustellen, sollten Tests auf die Kernfunktionalitäten abzielen und in GitHub-Workflows integrierbar sein. Das Projekt umfasst ein Django-basiertes Frontend mit Three.js und ifc.js für die Visualisierung von IFC-Dateien, ein FastAPI-Backend zur Markierung wiederverwendbarer Komponenten und eine Katalogansicht. Nachfolgend werden zwei Tests vorgeschlagen, die sich gut eignen: **Unit-Tests für Django-Views und FastAPI-Endpunkte** sowie **End-to-End-Tests für den IFC-Upload- und Auswahl-Workflow**. Beide Tests können über GitHub Actions automatisiert werden.

### 1. Unit-Tests für Django-Views und FastAPI-Endpunkte
**Beschreibung**:  
Unit-Tests überprüfen einzelne Komponenten der Anwendung isoliert, z. B. die Django-Views für die Visualisierungsseite (`reuse/select.html`) und die Katalogansicht (`catalog.html`) sowie den FastAPI-Endpunkt `/mark_reusable/`. Diese Tests stellen sicher, dass die Backend-Logik korrekt funktioniert, z. B. das Rendern von Vorlagen, das Verarbeiten von POST-Anfragen und das Aktualisieren von IFC-Dateien.

**Warum geeignet?**  
- **Relevanz**: Die Django-Views und der FastAPI-Endpunkt sind zentrale Komponenten für die Funktionalität der Website (IFC-Visualisierung, Auswahl und Wiederverwendbarkeitsmarkierung).  
- **GitHub-Integration**: Unit-Tests lassen sich einfach mit `pytest` in GitHub Actions automatisieren, um bei jedem Push oder Pull Request die Funktionalität zu überprüfen.  
- **Schnelligkeit**: Unit-Tests sind schnell und ideal für die kontinuierliche Integration (CI).

**Umsetzung**:  
1. **Django-Unit-Tests**:  
   - Erstelle Tests für die `catalog`-View, um sicherzustellen, dass wiederverwendbare Komponenten korrekt gefiltert werden.  
   - Beispiel in `frontend/tests/test_views.py`:  
     ```python
     from django.test import TestCase, Client
     from django.urls import reverse
     from frontend.models import Component

     class CatalogViewTest(TestCase):
         def setUp(self):
             self.client = Client()
             Component.objects.create(global_id="test_id_1", reuse_flag=True)
             Component.objects.create(global_id="test_id_2", reuse_flag=False)

         def test_catalog_view_filters_reusable(self):
             response = self.client.get(reverse('catalog'))
             self.assertEqual(response.status_code, 200)
             self.assertContains(response, "test_id_1")
             self.assertNotContains(response, "test_id_2")
     ```  
   - Teste die `select`-View, um sicherzustellen, dass die Vorlage korrekt gerendert wird:  
     ```python
     def test_select_view_renders_template(self):
         response = self.client.get(reverse('select'))
         self.assertEqual(response.status_code, 200)
         self.assertTemplateUsed(response, 'reuse/select.html')
     ```

2. **FastAPI-Unit-Tests**:  
   - Teste den `/mark_reusable/`-Endpunkt, um sicherzustellen, dass er POST-Anfragen korrekt verarbeitet und IFC-Dateien aktualisiert.  
   - Beispiel in `backend/tests/test_api.py`:  
     ```python
     from fastapi.testclient import TestClient
     from backend.main import app
     import ifcopenshell

     client = TestClient(app)

     def test_mark_reusable_endpoint():
         # Erstelle eine Test-IFC-Datei
         ifc_file = ifcopenshell.file()
         element = ifc_file.create_entity("IfcWall", GlobalId="test_guid")
         ifc_file.write("test.ifc")
         
         response = client.post("/mark_reusable/", json={
             "filename": "test.ifc",
             "reusable_ids": ["test_guid"]
         })
         assert response.status_code == 200
         assert response.json()["status"] == "success"
         
         # Überprüfe, ob Pset_Reuse hinzugefügt wurde
         updated_ifc = ifcopenshell.open("updated_test.ifc")
         element = updated_ifc.by_guid("test_guid")
         psets = [p for p in element.IsDefinedBy if p.RelatingPropertyDefinition.Name == "Pset_Reuse"]
         assert len(psets) > 0
     ```

3. **GitHub Actions Workflow**:  
   - Erstelle eine Workflow-Datei `.github/workflows/unit-tests.yml`:  
     ```yaml
     name: Unit-Tests
     on:
       push:
         branches: [ main ]
       pull_request:
         branches: [ main ]
     jobs:
       test:
         runs-on: ubuntu-latest
         steps:
         - uses: actions/checkout@v3
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.10'
         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip
             pip install pytest pytest-django fastapi uvicorn ifcopenshell
             pip install -r backend/requirements.txt
         - name: Run Django tests
           env:
             DJANGO_SETTINGS_MODULE: IfcReuseLibrary.settings
           run: pytest frontend/tests/
         - name: Run FastAPI tests
           run: pytest backend/tests/
     ```  
   - Dies automatisiert das Ausführen der Tests bei jedem Push oder Pull Request.

**Werkzeuge**:  
- `pytest` und `pytest-django` für Django-Tests  
- `fastapi.testclient` für FastAPI-Tests  
- `ifcopenshell` für IFC-Datei-Tests  
- GitHub Actions für CI  

### 2. End-to-End-Tests für den IFC-Upload- und Auswahl-Workflow
**Beschreibung**:  
End-to-End-Tests (E2E) simulieren das Benutzerverhalten, um den gesamten Workflow zu überprüfen: Hochladen einer IFC-Datei, Anzeigen im Viewer, Auswählen von Elementen, Absenden der Auswahl an den FastAPI-Endpunkt und Anzeigen der wiederverwendbaren Komponenten im Katalog. Diese Tests verwenden Tools wie Playwright, um die Benutzeroberfläche zu automatisieren.

**Warum geeignet?**  
- **Relevanz**: Der IFC-Upload- und Auswahl-Workflow ist die Kernfunktionalität der Website, die sowohl Frontend (Django, Three.js, ifc.js) als auch Backend (FastAPI, IfcOpenShell) umfasst.  
- **GitHub-Integration**: E2E-Tests können mit Playwright in GitHub Actions ausgeführt werden, um sicherzustellen, dass Benutzerinteraktionen wie erwartet funktionieren.  
- **Benutzerperspektive**: E2E-Tests decken Integrationen zwischen Frontend und Backend ab, die Unit-Tests möglicherweise übersehen.

**Umsetzung**:  
1. **Playwright-Test für den Workflow**:  
   - Installiere Playwright: `pip install pytest-playwright` und `playwright install`.  
   - Erstelle einen Test in `tests/e2e/test_ifc_workflow.py`:  
     ```python
     import pytest
     from playwright.sync_api import sync_playwright

     def test_ifc_upload_and_selection():
         with sync_playwright() as p:
             browser = p.chromium.launch()
             page = browser.new_page()
             
             # Starte Django- und FastAPI-Server (lokal oder in CI)
             page.goto("http://localhost:8000/select/")
             assert page.title() == "IFC Selektion"  # Passe den Titel an

             # Lade eine Test-IFC-Datei hoch
             page.set_input_files("#ifc-upload", "testdata/test.ifc")
             # Simuliere Auswahl (Klick im Viewer)
             page.click("#viewer")
             page.wait_for_selector("ul#selected-elements li")
             # Sende Auswahl ab
             page.click("#mark-reusable")
             page.wait_for_timeout(2000)  # Warte auf POST-Anfrage
             assert page.locator("text=Komponenten erfolgreich markiert").is_visible()

             # Überprüfe Katalog
             page.goto("http://localhost:8000/kors/")
             assert page.locator("text=test_guid").is_visible()

             browser.close()
     ```  
   - **Hinweis**: Die Auswahl im Three.js-Viewer ist schwierig zu automatisieren, daher ist dies eine vereinfachte Version. Mockups oder API-Hooks können verwendet werden, um die Auswahl zu simulieren.

2. **GitHub Actions Workflow**:  
   - Erstelle eine Workflow-Datei `.github/workflows/e2e-tests.yml`:  
     ```yaml
     name: End-to-End-Tests
     on:
       push:
         branches: [ main ]
       pull_request:
         branches: [ main ]
     jobs:
       test:
         runs-on: ubuntu-latest
         steps:
         - uses: actions/checkout@v3
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.10'
         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip
             pip install pytest pytest-playwright django fastapi uvicorn ifcopenshell
             pip install -r backend/requirements.txt
             playwright install
         - name: Start Django server
           env:
             DJANGO_SETTINGS_MODULE: IfcReuseLibrary.settings
           run: |
             python manage.py runserver 0.0.0.0:8000 &
             sleep 5  # Warte auf Serverstart
         - name: Start FastAPI server
           run: |
             cd backend
             uvicorn main:app --host 0.0.0.0 --port 8001 &
             sleep 5
         - name: Run E2E tests
           run: pytest tests/e2e/
     ```  
   - Dies startet beide Server im Hintergrund und führt die Playwright-Tests aus.

**Werkzeuge**:  
- `pytest-playwright` für E2E-Tests  
- `playwright` für Browser-Automatisierung  
- Test-IFC-Datei (z. B. `testdata/test.ifc`)  
- GitHub Actions für CI  

## Warum diese Tests?
- **Unit-Tests**: Sie sind schnell, gezielt und decken die Backend-Logik (Django-Views, FastAPI-Endpunkte, IFC-Verarbeitung) ab, die für die Kernfunktionalität entscheidend ist.  
- **E2E-Tests**: Sie simulieren den Benutzer-Workflow und stellen sicher, dass Frontend und Backend nahtlos zusammenarbeiten, was besonders für die Visualisierungs- und Katalogfunktionen wichtig ist.  
- **GitHub Actions**: Beide Tests lassen sich gut in GitHub-Workflows integrieren, um automatische Überprüfungen bei Code-Änderungen zu gewährleisten.

## Zusätzliche Hinweise
- **Testdaten**: Erstelle eine kleine Test-IFC-Datei (z. B. mit IfcOpenShell), um die Tests reproduzierbar zu machen. Speichere sie in `testdata/`.  
- **Abdeckung**: Nutze `pytest-cov`, um die Testabdeckung zu messen:  
  ```bash
  pip install pytest-cov
  pytest --cov=frontend --cov=backend
  ```  
- **Voraussetzungen**: Stelle sicher, dass alle Abhängigkeiten (`django`, `fastapi`, `ifcopenshell`, etc.) in deinem virtuellen Environment installiert sind, wie im Repository beschrieben.  
- **Fehlerbehandlung**: Füge in den Tests Assertions für Fehlerszenarien hinzu (z. B. ungültige IFC-Dateien oder fehlende GlobalIds).  

## Beispiel für Test-Setup im Repository
1. Erstelle ein `tests/`-Verzeichnis im Root des Repositories:  
   ```
   IfcReuseLibrary/
   ├── backend/
   │   ├── tests/
   │   │   └── test_api.py
   │   └── requirements.txt
   ├── frontend/
   │   ├── tests/
   │   │   └── test_views.py
   ├── tests/
   │   ├── e2e/
   │   │   └── test_ifc_workflow.py
   │   └── testdata/
   │       └── test.ifc
   └── .github/
       └── workflows/
           ├── unit-tests.yml
           └── e2e-tests.yml
   ```  
2. Füge die oben genannten Testdateien und Workflows hinzu.  
3. Commit und push die Änderungen, um die Tests in GitHub Actions auszuführen.

## Nächste Schritte
- **Unit-Tests einrichten**: Beginne mit den Django- und FastAPI-Unit-Tests, da sie schneller zu implementieren sind.  
- **E2E-Tests ergänzen**: Füge E2E-Tests hinzu, sobald die Unit-Tests stabil sind, um den vollständigen Workflow zu validieren.  
- **Fehlermeldungen teilen**: Wenn du beim Einrichten der Tests auf Fehler stößt (z. B. bei Playwright oder GitHub Actions), teile die Fehlermeldung, damit ich helfen kann.  
- **Repository-Status**: Falls dein lokales Projekt immer noch kein `backend/`-Verzeichnis enthält (wie zuvor erwähnt), kläre, ob du das vollständige Repository geklont hast oder ein separates Projekt verwendest.

Falls du weitere Details (z. B. spezifische Testfälle oder Hilfe bei der Implementierung) benötigst, lass es mich wissen!
