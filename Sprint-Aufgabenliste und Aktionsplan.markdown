# Sprint-Aufgabenliste und Aktionsplan

Um die zweiwöchige Sprint-Aufgabenliste für den Aufbau einer neuen Visualisierungsseite und der zugehörigen Backend-Funktionalität anzugehen, folgt hier eine klare Aufschlüsselung der Aufgaben, organisiert nach Priorität und Zeitplan, mit umsetzbaren Schritten, um jede Aufgabe effizient zu erledigen. Ich werde auch optionale Erweiterungen ansprechen und Werkzeuge oder Ansätze für mehr Klarheit vorschlagen. Das Ziel ist es, ein Django-basiertes Frontend mit Three.js und ifc.js für die Visualisierung von IFC-Dateien zu erstellen, ein FastAPI-Backend zur Handhabung der Markierung wiederverwendbarer Komponenten und eine Katalogansicht mit Indikatoren für den Wiederverwendbarkeitsstatus, einschließlich Tests und Feinschliff.

## Aufschlüsselung und Aktionsplan des Sprints

### 🔹 1. Frontend: Neue Visualisierungsseite (Tage 1–3)
**Ziel**: Erstellung einer Django-Vorlage mit einem Three.js-basierten Viewer unter Verwendung von ifc.js, um IFC-Dateien zu laden, anzuzeigen und Elemente auszuwählen, die Auswahl zu speichern und visuell hervorzuheben.

- **Django-Vorlage erstellen (reuse/select.html)**:
  - Erstelle in deinem Django-Projekt eine neue Vorlage unter `templates/reuse/select.html`.
  - Richte eine grundlegende HTML-Struktur ein mit einem `<div id="viewer">` für die Three.js-Leinwand und einem Datei-Upload-Feld für IFC-Dateien (`<input type="file" id="ifc-upload" accept=".ifc">`).
  - Füge einen Bereich hinzu, um ausgewählte GlobalIds anzuzeigen (z. B. `<ul id="selected-elements">`).
  - Beispielstruktur:
    ```html
    {% extends 'base.html' %}
    {% block content %}
      <div id="viewer" style="width: 100%; height: 500px;"></div>
      <input type="file" id="ifc-upload" accept=".ifc">
      <h3>Ausgewählte Elemente</h3>
      <ul id="selected-elements"></ul>
    {% endblock %}
    ```

- **Three.js-Szene einrichten**:
  - Binde Three.js über CDN ein: `<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>`.
  - Initialisiere eine Three.js-Szene mit:
    - **Szene**: `const scene = new THREE.Scene();`
    - **Kamera**: `const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);`
    - **Renderer**: `const renderer = new THREE.WebGLRenderer(); renderer.setSize(window.innerWidth, 500);`
    - **Lichter**: Füge Umgebungs- und Richtungslicht hinzu (z. B. `new THREE.AmbientLight(0x404040)` und `new THREE.DirectionalLight(0xFFFFFF, 0.5)`).
    - Füge den Renderer dem `#viewer`-Div hinzu: `document.getElementById('viewer').appendChild(renderer.domElement);`.
    - Aktiviere Orbit-Steuerung für Navigation: `<script src="https://threejs.org/examples/js/controls/OrbitControls.js"></script>` und `const controls = new THREE.OrbitControls(camera, renderer.domElement);`.

- **ifc.js integrieren**:
  - Binde ifc.js über CDN ein: `<script src="https://unpkg.com/web-ifc-viewer@1.0.217/dist/ifc.js"></script>` (verwende die neueste Version).
  - Initialisiere den IFC-Viewer: `const viewer = new IfcViewerAPI({ container: document.getElementById('viewer') });`.
  - Stelle sicher, dass der Viewer mit der Three.js-Szene kompatibel ist, indem du `viewer.IFC.setWasmPath("path/to/wasm/");` setzt, falls erforderlich (prüfe die ifc.js-Dokumentation für den aktuellen WASM-Pfad).

- **Datei-Loader hinzufügen**:
  - Füge einen Event-Listener für das Datei-Upload-Feld hinzu:
    ```javascript
    document.getElementById('ifc-upload').addEventListener('change', async (event) => {
      const file = event.target.files[0];
      const url = URL.createObjectURL(file);
      await viewer.IFC.loadIfcUrl(url);
    });
    ```
  - Speichere den Dateinamen für spätere Verwendung (z. B. `const filename = file.name;` in einer globalen Variable).

- **Raycasting für Auswahl aktivieren**:
  - Nutze die integrierte Auswahl-API von ifc.js: `viewer.IFC.selector`, um Elemente per Klick auszuwählen.
  - Beispiel:
    ```javascript
    viewer.IFC.selector.prePickIfcItemsByID(0, [], true); // Vorauswahl für Raycasting
    window.addEventListener('click', async () => {
      const found = await viewer.IFC.selector.pickIfcItem(true);
      if (found) {
        const globalId = found.modelID; // Anpassen an ifc.js-API
        selectedGuids.push(globalId);
        updateSelectedElementsList();
      }
    });
    ```
  - Speichere ausgewählte GlobalIds in einem Array: `let selectedGuids = [];`.

- **Ausgewählte Elemente hervorheben**:
  - Verwende ifc.js, um Elemente durch Änderung des Materials oder der Farbe hervorzuheben:
    ```javascript
    viewer.IFC.setMaterial(found.modelID, found.id, new THREE.MeshBasicMaterial({ color: 0xFF0000 }));
    ```
  - Aktualisiere die Benutzeroberfläche, um ausgewählte GlobalIds anzuzeigen:
    ```javascript
    function updateSelectedElementsList() {
      const list = document.getElementById('selected-elements');
      list.innerHTML = selectedGuids.map(id => `<li>${id}</li>`).join('');
    }
    ```

**Werkzeuge/Abhängigkeiten**:
  - Three.js (CDN)
  - ifc.js (CDN)
  - Django für Vorlagen
  - Stelle sicher, dass `STATICFILES_DIRS` in `settings.py` benutzerdefinierte JS/CSS-Dateien enthält, falls nötig.

**Zeitaufwand**: ~3 Tage (1 Tag für Vorlage und Three.js-Setup, 1 Tag für ifc.js-Integration, 1 Tag für Raycasting und Hervorhebung).

### 🔹 2. Frontend: Auswahl absenden (Tage 4–5)
**Ziel**: Einen Button hinzufügen, um ausgewählte GlobalIds und den Dateinamen an einen FastAPI-Endpunkt per POST-Anfrage zu senden.

- **Button „Als wiederverwendbar markieren“ hinzufügen**:
  - Füge in `select.html` einen Button hinzu: `<button id="mark-reusable">Als wiederverwendbar markieren</button>`.
  - Gestalte ihn auffällig (z. B. mit Bootstrap oder benutzerdefiniertem CSS).

- **fetch()-POST-Anfrage implementieren**:
  - Füge einen Event-Listener für den Button hinzu:
    ```javascript
    document.getElementById('mark-reusable').addEventListener('click', async () => {
      const data = { filename, selectedGuids };
      try {
        const response = await fetch('/api/mark_reusable/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        if (response.ok) {
          alert('Komponenten erfolgreich als wiederverwendbar markiert!');
          selectedGuids = []; // Auswahl zurücksetzen
          updateSelectedElementsList();
        } else {
          alert('Fehler beim Absenden der Auswahl');
        }
      } catch (error) {
        console.error('Fehler beim Absenden:', error);
        alert('Absenden fehlgeschlagen');
      }
    });
    ```

**Werkzeuge/Abhängigkeiten**:
  - Fetch-API (nativ)
  - Stelle sicher, dass CORS in FastAPI konfiguriert ist, um Anfragen vom Django-Frontend zu akzeptieren.

**Zeitaufwand**: ~2 Tage (1 Tag für Button und fetch-Setup, 1 Tag für Fehlerbehandlung und Tests).

### 🔹 3. Backend: FastAPI-Endpunkt (Tage 5–7)
**Ziel**: Einen FastAPI-Endpunkt erstellen, der Dateinamen und GlobalIds verarbeitet, die IFC-Datei mit einer Wiederverwendbarkeitseigenschaft aktualisiert und optional eine PostgreSQL-Datenbank aktualisiert.

- **POST-Route /mark_reusable/ erstellen**:
  - Definiere in deinem FastAPI-Projekt ein Pydantic-Modell:
    ```python
    from pydantic import BaseModel
    class ReuseRequest(BaseModel):
        filename: str
        reusable_ids: list[str]
    ```
  - Erstelle den Endpunkt:
    ```python
    from fastapi import FastAPI
    app = FastAPI()
    @app.post("/mark_reusable/")
    async def mark_reusable(request: ReuseRequest):
        return {"status": "success", "filename": request.filename, "ids": request.reusable_ids}
    ```

- **IFC-Datei mit IfcOpenShell verarbeiten**:
  - Installiere IfcOpenShell: `pip install ifcopenshell`.
  - Lade und bearbeite die IFC-Datei:
    ```python
    import ifcopenshell
    def update_ifc_reuse(filename: str, reusable_ids: list[str]):
        ifc_file = ifcopenshell.open(f"path/to/ifc/files/{filename}")
        for global_id in reusable_ids:
            element = ifc_file.by_guid(global_id)
            if element:
                pset = ifcopenshell.api.run("pset.add_pset", ifc_file, product=element, name="Pset_Reuse")
                ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=pset, properties={"Reusable": True})
        new_filename = f"path/to/ifc/files/updated_{filename}"
        ifc_file.write(new_filename)
        return new_filename
    ```
  - Integriere in den Endpunkt:
    ```python
    @app.post("/mark_reusable/")
    async def mark_reusable(request: ReuseRequest):
        new_filename = update_ifc_reuse(request.filename, request.reusable_ids)
        return {"status": "success", "new_filename": new_filename}
    ```

- **Optional: PostgreSQL aktualisieren**:
  - Wenn eine Datenbank verwendet wird, verbinde dich mit PostgreSQL über `psycopg2` oder `SQLAlchemy`.
  - Beispiel mit SQLAlchemy:
    ```python
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("postgresql://user:password@localhost/dbname")
    Session = sessionmaker(bind=engine)
    def update_reuse_flag(global_ids: list[str]):
        with Session() as session:
            session.execute(update(Component).where(Component.global_id.in_(global_ids)).values(reuse_flag=True))
            session.commit()
    ```
  - Rufe `update_reuse_flag(request.reusable_ids)` im Endpunkt auf.

**Werkzeuge/Abhängigkeiten**:
  - FastAPI (`pip install fastapi uvicorn`)
  - IfcOpenShell (`pip install ifcopenshell`)
  - Pydantic (enthalten in FastAPI)
  - SQLAlchemy oder psycopg2 für PostgreSQL (optional)

**Zeitaufwand**: ~3 Tage (1 Tag für Endpunkt-Setup, 1 Tag für IfcOpenShell-Integration, 1 Tag für Datenbank und Tests).

### 🔹 4. Backend: Katalogansicht aktualisieren (Tage 8–10)
**Ziel**: Die Django-Katalogansicht anpassen, um wiederverwendbare Komponenten anzuzeigen und die Kompatibilität mit GLB-Vorschauen sicherzustellen.

- **catalog() in views.py anpassen**:
  - Aktualisiere die Ansicht, um Komponenten mit `reuse_flag=True` zu filtern (bei Verwendung von PostgreSQL):
    ```python
    from django.shortcuts import render
    from .models import Component
    def catalog(request):
        reusable_components = Component.objects.filter(reuse_flag=True)
        return render(request, 'catalog.html', {'components': reusable_components})
    ```
  - Ohne Datenbank: Scanne IFC-Dateien nach `Pset_Reuse`-Eigenschaften:
    ```python
    import ifcopenshell
    def get_reusable_components():
        reusable = []
        for file_path in os.listdir("path/to/ifc/files"):
            ifc_file = ifcopenshell.open(f"path/to/ifc/files/{file_path}")
            for element in ifc_file.by_type("IfcElement"):
                psets = element.IsDefinedBy
                for pset in psets:
                    if pset.RelatingPropertyDefinition.Name == "Pset_Reuse":
                        for prop in pset.RelatingPropertyDefinition.HasProperties:
                            if prop.Name == "Reusable" and prop.NominalValue.wrappedValue:
                                reusable.append({"global_id": element.GlobalId, "file": file_path})
        return reusable
    ```

- **Visuellen Indikator hinzufügen**:
  - Füge in `catalog.html` ein Abzeichen oder eine Farbe für wiederverwendbare Komponenten hinzu:
    ```html
    {% for component in components %}
      <div class="component {% if component.reuse_flag %}reusable{% endif %}">
        {{ component.global_id }} {% if component.reuse_flag %}<span class="badge bg-success">Wiederverwendbar</span>{% endif %}
      </div>
    {% endfor %}
    ```
  - CSS: `.reusable { background-color: #e6ffe6; }`.

- **GLB-Vorschauen sicherstellen**:
  - Falls GLB-Dateien verwendet werden, konvertiere aktualisierte IFC-Dateien mit einem Tool wie `ifcConvert` in GLB.
  - Speichere GLB-Dateien in einem statischen Verzeichnis und verlinke sie im Katalog:
    ```html
    <a href="/static/glb/{{ component.global_id }}.glb">3D-Vorschau</a>
    ```

**Werkzeuge/Abhängigkeiten**:
  - Django ORM oder IfcOpenShell für Datenabfragen
  - Bootstrap oder benutzerdefiniertes CSS für Styling
  - IfcConvert oder ähnliches für GLB-Konvertierung (falls zutreffend)

**Zeitaufwand**: ~3 Tage (1 Tag für Logik der Ansicht, 1 Tag für Vorlagenaktualisierung, 1 Tag für GLB-Handhabung und Tests).

### 🔹 5. Testen und Feinschliff (Tage 11–14)
**Ziel**: Sicherstellen, dass der gesamte Workflow funktioniert, browserübergreifend kompatibel ist und benutzerfreundlich ist, mit Dokumentation.

- **Kompletten Workflow testen**:
  - Lade eine IFC-Datei hoch, zeige sie an, wähle Elemente aus, sende sie ab und überprüfe die aktualisierte Datei und den Katalog.
  - Überprüfe, ob `Pset_Reuse` korrekt hinzugefügt wurde und der Katalog wiederverwendbare Komponenten anzeigt.

- **Browserübergreifende Tests**:
  - Teste auf Chrome und Firefox (nutze BrowserStack oder lokale VMs, falls nötig).
  - Überprüfe, ob Three.js- und ifc.js-Rendering, Datei-Uploads und POST-Anfragen konsistent funktionieren.

- **Fehlerbehandlung**:
  - Füge Prüfungen für fehlende Dateien hinzu:
    ```python
    if not os.path.exists(f"path/to/ifc/files/{filename}"):
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    ```
  - Behandle ungültige GlobalIds in FastAPI:
    ```python
    for global_id in reusable_ids:
        if not ifc_file.by_guid(global_id):
            raise HTTPException(status_code=400, detail=f"Ungültige GlobalId: {global_id}")
    ```
  - Zeige benutzerfreundliche Warnungen im Frontend für Fehler (z. B. `alert('Ungültige Datei oder Auswahl')`).

- **UI/UX überprüfen**:
  - Stelle sicher, dass Buttons klar positioniert sind (z. B. „Als wiederverwendbar markieren“ unter dem Viewer).
  - Füge Bestätigungsnachrichten nach dem Absenden hinzu (z. B. `alert('Auswahl gespeichert!')`).
  - Verbessere die visuelle Klarheit mit CSS (z. B. ausgewählte Elemente in einer auffälligen Farbe wie Rot hervorheben).

- **Dokumentation schreiben**:
  - Erstelle eine `README.md`-Datei oder eine Wiki-Seite mit:
    - Anleitung zum Hochladen und Anzeigen von IFC-Dateien.
    - Anleitung zum Auswählen und Markieren von Komponenten als wiederverwendbar.
    - Anleitung zum Anzeigen wiederverwendbarer Komponenten im Katalog.
    - Installationsanweisungen (Abhängigkeiten, FastAPI/Django-Setup, PostgreSQL-Konfiguration, falls verwendet).
  - Beispielstruktur:
    ```
    # IFC-Wiederverwendungs-Workflow
    ## Überblick
    Diese App ermöglicht das Hochladen von IFC-Dateien, das Auswählen von Komponenten, deren Markierung als wiederverwendbar und deren Anzeige im Katalog.
    ## Einrichtung
    1. Installiere Abhängigkeiten: `pip install -r requirements.txt`
    2. Starte FastAPI: `uvicorn main:app --reload`
    3. Starte Django: `python manage.py runserver`
    ## Nutzung
    - Hochladen: Wähle eine IFC-Datei auf der Visualisierungsseite aus.
    - Auswählen: Klicke auf Elemente, um sie zu markieren.
    - Absenden: Klicke auf „Als wiederverwendbar markieren“, um zu speichern.
    - Katalog: Zeige wiederverwendbare Komponenten mit Abzeichen an.
    ```

**Werkzeuge/Abhängigkeiten**:
  - BrowserStack oder lokale Browser für Tests
  - Markdown für Dokumentation

**Zeitaufwand**: ~4 Tage (1 Tag für Workflow-Tests, 1 Tag für Browser-Tests, 1 Tag für Fehlerbehandlung/UI, 1 Tag für Dokumentation).

### 📌 Optionale Erweiterungen (Stretch Goals)
Falls Zeit bleibt, priorisiere diese nach Relevanz:

- **Abwählen von Komponenten ermöglichen**:
  - Füge eine Abwahl-Option im Viewer hinzu:
    ```javascript
    viewer.IFC.selector.unpickIfcItems();
    selectedGuids = selectedGuids.filter(id => id !== deselectedId);
    updateSelectedElementsList();
    ```
  - Füge einen „Entfernen“-Button neben jeder aufgelisteten GlobalId in der UI hinzu.

- **Notizen/Kommentare hinzufügen**:
  - Erweitere das Pydantic-Modell: `notes: Optional[str] = None`.
  - Füge ein Textfeld in `select.html` hinzu: `<textarea id="notes"></textarea>`.
  - Füge Notizen zur POST-Anfrage hinzu und speichere sie mit IfcOpenShell in `Pset_Reuse`.

- **localStorage/sessionStorage verwenden**:
  - Speichere Auswahlen: `localStorage.setItem('selectedGuids', JSON.stringify(selectedGuids));`.
  - Stelle bei Seitenladevorgang wieder her: `selectedGuids = JSON.parse(localStorage.getItem('selectedGuids')) || [];`.

- **Lade-Indikatoren/Erfolgsmeldungen hinzufügen**:
  - Nutze einen Spinner während Datei-Upload und POST-Anfragen:
    ```html
    <div id="loading" style="display: none;">Lädt...</div>
    ```
    ```javascript
    document.getElementById('loading').style.display = 'block';
    // Nach fetch: document.getElementById('loading').style.display = 'none';
    ```
  - Verwende Bootstrap-Modals für Erfolgsmeldungen:
    ```html
    <div class="modal" id="successModal">
      <div class="modal-content">Komponenten erfolgreich markiert!</div>
    </div>
    ```

**Zeitaufwand**: ~1–2 Tage, falls priorisiert (über den Sprint verteilt, wenn Zeit bleibt).

## Tipps zur Umsetzung
- **Tagesplan**:
  - **Tage 1–2**: Richte Django-Vorlage und Three.js/ifc.js-Integration ein.
  - **Tag 3**: Schließe Raycasting und Hervorhebung ab.
  - **Tage 4–5**: Entwickle und teste die Absende-Funktion.
  - **Tage 6–7**: Entwickle und teste den FastAPI-Endpunkt mit IfcOpenShell.
  - **Tage 8–9**: Aktualisiere die Katalogansicht und bearbeite GLB-Vorschauen.
  - **Tage 10–14**: Teste gründlich, verfeinere die UI und erstelle Dokumentation.
- **Zusammenarbeit**:
  - Bei Teamarbeit: Teile Frontend (Aufgaben 1–2) und Backend (Aufgaben 3–4) auf.
  - Nutze Git für Versionskontrolle; erstelle Branches für jede Aufgabe (z. B. `feature/visualization-page`, `feature/fastapi-endpoint`).
- **Frühes Testen**:
  - Teste das Laden und Auswählen von IFC-Dateien bis Tag 3, um ifc.js-Probleme früh zu erkennen.
  - Validiere den FastAPI-Endpunkt mit einer Beispiel-IFC-Datei bis Tag 7.
- **Werkzeuge**:
  - Nutze VS Code mit Python- und JavaScript-Erweiterungen für Linting.
  - Verwende Postman, um FastAPI-Endpunkte zu testen.
  - Nutze Django Debug Toolbar für das Debugging von Ansichten.

## Mögliche Herausforderungen und Lösungen
- **ifc.js-Kompatibilität**: Stelle sicher, dass die CDN-Version deine IFC-Dateien unterstützt; teste frühzeitig mit einer Beispiel-IFC-Datei.
- **CORS-Probleme**: Konfiguriere FastAPI mit `fastapi.middleware.cors`:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8000"], allow_methods=["*"], allow_headers=["*"])
  ```
- **Große IFC-Dateien**: Optimiere das Laden mit den Streaming-Funktionen von ifc.js oder erwäge serverseitige Vorverarbeitung.
- **GLB-Konvertierung**: Automatisiere die IFC-zu-GLB-Konvertierung mit einem Skript oder Tool wie `ifcConvert`; teste die Kompatibilität mit Three.js.

## Abschließende Hinweise
- Beginne mit einem minimal funktionsfähigen Workflow (Hochladen, Auswählen, Speichern, Anzeigen), bevor du optionale Erweiterungen hinzufügst.
- Halte die Dokumentation präzise, aber klar für zukünftige Entwickler oder Nutzer.
- Bei Blockaden (z. B. ifc.js-Fehler) prüfe die ifc.js-GitHub-Issues oder X-Posts für Community-Lösungen.
- Für Fragen zu Preisen oder Abonnements von xAI-Produkten (z. B. SuperGrok) verweise ich auf https://x.ai/grok, aber dieses Projekt scheint eigenständig zu sein.

Falls du spezifische Code-Snippets, Hilfe beim Debugging oder Klärungen zu einer Aufgabe benötigst, lass es mich wissen!