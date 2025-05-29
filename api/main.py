"""
main.py: FastAPI-Backend zur Verarbeitung von IFC-Dateien, Konvertierung zu GLB und Markierung von wiederverwendbaren Komponenten.
Integriert Projektverwaltung, IFC-zu-GLB-Konvertierung und Wiederverwendbarkeitsmarkierung mit PostgreSQL.
"""

import os
import shutil
import logging
import subprocess
from datetime import datetime
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.element
from sqlalchemy.orm import Session
from api.database import SessionLocal, Base, User, Project, Component, engine

# Konfiguration des Loggings für Debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisierung der FastAPI-Anwendung
app = FastAPI(
    title="IFC Wiederverwendung API",
    description="API zur Verarbeitung von IFC-Dateien, Konvertierung zu GLB und Markierung von wiederverwendbaren Komponenten",
    version="1.0.0"
)

# CORS-Konfiguration für das Django-Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfiguration der Verzeichnisse
BUCKET_FOLDER = os.path.join("uploads", "ifc-bucket")  # Verzeichnis für hochgeladene IFC-Dateien
GLB_FOLDER = os.path.join("uploads", "glb")  # Verzeichnis für GLB-Dateien
TEMP_FOLDER = os.path.join("uploads", "temp_ifcs")  # Temporäres Verzeichnis für IFC-Dateien
IFC_FILES_FOLDER = os.path.join("uploads", "ifc_files")  # Verzeichnis für aktualisierte IFC-Dateien
os.makedirs(BUCKET_FOLDER, exist_ok=True)
os.makedirs(GLB_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(IFC_FILES_FOLDER, exist_ok=True)

# Konfiguration von IfcConvert
# Konfiguration von IfcConvert
IFCCONVERT_PATH = "/usr/local/bin/IfcConvert"  # Pfad zu IfcConvert für macOS  # Pfad zu IfcConvert anpassen

# Unterstützte IFC-Komponententypen
COMPONENT_TYPES = ["IfcWall", "IfcWindow", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcSpace"]

# Pydantic-Modell für die POST-Anfrage an /api/mark_reusable/
class ReuseRequest(BaseModel):
    filename: str
    selectedGuids: List[str]  # Angepasst an das Frontend

    class Config:
        schema_extra = {
            "example": {
                "filename": "beispiel.ifc",
                "selectedGuids": ["2x0sZ9X6n0m9K9Y9Z9X6n0", "3y1tA0B7p1n2L8Z8A0B7p1"]
            }
        }

# Pydantic-Modelle für Projekte und Komponenten
class ComponentModel(BaseModel):
    id: str = Field(...)
    name: str
    type: str

class ProjectModel(BaseModel):
    id: str
    name: str
    components: List[ComponentModel] = []

# Abhängigkeit für Datenbanksitzung
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funktion zum Exportieren eines einzelnen Elements in eine IFC-Datei
def export_single_element_to_ifc(model, element, output_path):
    """Exportiert ein einzelnes IFC-Element in eine neue IFC-Datei."""
    try:
        new_model = ifcopenshell.file()
        new_model.add(element)
        new_model.write(output_path)
        logger.info(f"Element nach {output_path} exportiert")
    except Exception as e:
        logger.error(f"Fehler beim Exportieren des IFC-Elements: {str(e)}")
        raise

# Funktion zur Konvertierung von IFC-Komponenten zu GLB
def convert_ifc_components_to_glb(ifc_path, output_glb_dir, project_id, db: Session):
    """Konvertiert IFC-Komponenten in GLB-Dateien mit IfcConvert und speichert Komponenten in der Datenbank."""
    try:
        model = ifcopenshell.open(ifc_path)
        total = 0
        errors = []

        for comp_type in COMPONENT_TYPES:
            elements = model.by_type(comp_type)
            logger.info(f"{comp_type}: {len(elements)} Elemente gefunden")

            for element in elements:
                guid = element.GlobalId
                glb_filename = f"{guid}_{comp_type}.glb"
                glb_output_path = os.path.join(output_glb_dir, glb_filename)
                temp_ifc_path = os.path.join(TEMP_FOLDER, f"{guid}.ifc")

                try:
                    export_single_element_to_ifc(model, element, temp_ifc_path)
                    command = [IFCCONVERT_PATH, temp_ifc_path, glb_output_path, "--use-element-guids"]
                    result = subprocess.run(command, check=True, capture_output=True, text=True)
                    if os.path.exists(glb_output_path):
                        logger.info(f"{glb_filename} erstellt")
                        total += 1
                        # Komponente in der Datenbank speichern
                        component = Component(
                            project_id=project_id,
                            global_id=guid,
                            category=comp_type.replace("Ifc", ""),
                            name=comp_type.replace("Ifc", ""),
                            type=comp_type,
                            reuse_flag=False,
                            preview_url=glb_output_path
                        )
                        db.add(component)
                    else:
                        logger.warning(f"{glb_filename} nicht erstellt")
                        errors.append(guid)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Fehler beim Konvertieren von {guid}: {e.stderr}")
                    errors.append(guid)
                except Exception as e:
                    logger.error(f"Unerwarteter Fehler für {guid}: {str(e)}")
                    errors.append(guid)
                finally:
                    if os.path.exists(temp_ifc_path):
                        try:
                            os.remove(temp_ifc_path)
                        except Exception as e:
                            logger.warning(f"Konnte {temp_ifc_path} nicht löschen: {str(e)}")
        db.commit()
        logger.info(f"Zusammenfassung: {total} GLB-Dateien erstellt, {len(errors)} Fehler")
        return total, errors
    except Exception as e:
        db.rollback()
        logger.error(f"Fehler in convert_ifc_components_to_glb: {str(e)}")
        raise

# Funktion zum Aktualisieren der Wiederverwendbarkeitseigenschaft in IFC
def update_ifc_reuse(filename: str, selected_guids: List[str], project_id, db: Session) -> str:
    """Aktualisiert die IFC-Datei, indem Elemente als wiederverwendbar markiert werden, und aktualisiert die Datenbank."""
    ifc_path = os.path.join(IFC_FILES_FOLDER, filename)
    if not os.path.exists(ifc_path):
        raise HTTPException(status_code=404, detail=f"Datei {filename} nicht gefunden unter {ifc_path}")

    try:
        ifc_file = ifcopenshell.open(ifc_path)
        for global_id in selected_guids:
            if len(global_id) != 22:
                logger.warning(f"Ungültige GlobalId: {global_id} (muss 22 Zeichen haben)")
                continue
            element = ifc_file.by_guid(global_id)
            if element:
                pset = ifcopenshell.util.element.get_psets(element, qto=False).get("Pset_Reuse")
                if not pset:
                    pset = ifcopenshell.api.run("pset.add_pset", ifc_file, product=element, name="Pset_Reuse")
                ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=pset, properties={"Reusable": True})
                logger.info(f"Element {global_id} als wiederverwendbar markiert")
                # Aktualisiere reuse_flag in der Datenbank
                component = db.query(Component).filter_by(global_id=global_id, project_id=project_id).first()
                if component:
                    component.reuse_flag = True
                else:
                    # Erstelle neuen Komponenteneintrag, falls nicht vorhanden
                    component = Component(
                        project_id=project_id,
                        global_id=global_id,
                        category="Unknown",
                        name="Unknown",
                        type="Unknown",
                        reuse_flag=True
                    )
                    db.add(component)
            else:
                logger.warning(f"Kein Element mit GlobalId {global_id} gefunden")
        db.commit()

        new_filename = f"updated_{filename}"
        new_path = os.path.join(IFC_FILES_FOLDER, new_filename)
        ifc_file.write(new_path)
        logger.info(f"Aktualisierte IFC-Datei gespeichert unter {new_path}")
        return new_filename
    except Exception as e:
        db.rollback()
        logger.error(f"Fehler beim Aktualisieren der IFC-Datei: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Aktualisieren der IFC-Datei: {str(e)}")

# Endpunkt zum Hochladen von IFC-Dateien
@app.post("/upload")
async def upload_ifc_file(
    file: UploadFile = File(...),
    projectName: str = Form(...),
    location: str = Form(...),
    db: Session = Depends(get_db)
):
    """Lädt eine IFC-Datei hoch, verarbeitet sie und konvertiert Komponenten zu GLB."""
    try:
        file_path = os.path.join(BUCKET_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ifc_files_path = os.path.join(IFC_FILES_FOLDER, file.filename)
        shutil.copy(file_path, ifc_files_path)

        model = ifcopenshell.open(file_path)
        summary = {
            "filename": file.filename,
            "walls": len(model.by_type("IfcWall")),
            "windows": len(model.by_type("IfcWindow")),
            "slabs": len(model.by_type("IfcSlab")),
            "beams": len(model.by_type("IfcBeam")),
            "columns": len(model.by_type("IfcColumn")),
            "doors": len(model.by_type("IfcDoor")),
            "spaces": len(model.by_type("IfcSpace")),
        }

        user = db.query(User).filter_by(id="mock-user-id").first()
        if not user:
            user = User(
                id="mock-user-id",
                name="Test Benutzer",
                email="test@example.com",
                password_hash="hash",
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()

        project = Project(
            user_id=user.id,
            name=projectName,
            description="Hochgeladen über Formular",
            location=location,
            filename=file.filename,
            created_at=datetime.utcnow()
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        project_glb_dir = os.path.join(GLB_FOLDER, os.path.splitext(file.filename)[0])
        os.makedirs(project_glb_dir, exist_ok=True)
        total, errors = convert_ifc_components_to_glb(file_path, project_glb_dir, project.id, db)
        summary["glb_files_created"] = total
        summary["failed_components"] = errors

        return {
            "message": "IFC-Datei erfolgreich hochgeladen, verarbeitet und Komponenten zu GLB konvertiert",
            "data": summary
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Fehler im /upload Endpunkt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der Datei: {str(e)}")

# Endpunkt zum Markieren von Komponenten als wiederverwendbar
@app.post("/api/mark_reusable/")
async def mark_reusable(request: ReuseRequest, db: Session = Depends(get_db)):
    """Markiert IFC-Elemente als wiederverwendbar und aktualisiert die Datenbank."""
    try:
        if not request.selectedGuids:
            raise HTTPException(status_code=400, detail="Keine GlobalIds angegeben")
        # Finde das Projekt basierend auf dem Dateinamen
        project = db.query(Project).filter_by(filename=request.filename).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Projekt für Datei {request.filename} nicht gefunden")
        new_filename = update_ifc_reuse(request.filename, request.selectedGuids, project.id, db)
        return {
            "status": "success",
            "message": "Komponenten erfolgreich als wiederverwendbar markiert",
            "new_filename": new_filename
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Fehler im /api/mark_reusable/ Endpunkt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Verarbeiten der Anfrage: {str(e)}")

# Endpunkt zum Bereitstellen von GLB-Dateien
@app.get("/components/{component_id}/glb")
def serve_glb(component_id: str):
    """Liefert eine GLB-Datei für eine bestimmte Komponente."""
    try:
        for root, _, files in os.walk(GLB_FOLDER):
            for file in files:
                if file.startswith(component_id) and file.endswith(".glb"):
                    return FileResponse(os.path.join(root, file), media_type="model/gltf-binary")
        raise HTTPException(status_code=404, detail="GLB-Datei nicht gefunden")
    except Exception as e:
        logger.error(f"Fehler beim Bereitstellen der GLB-Datei für {component_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Bereitstellen der GLB-Datei: {str(e)}")

# Endpunkt zum Abrufen von Projekten
@app.get("/projects/")
def get_projects(db: Session = Depends(get_db)):
    """Ruft alle Projekte und ihre Komponenten ab."""
    try:
        projects = db.query(Project).all()
        project_models = []
        for project in projects:
            glb_dir = os.path.join(GLB_FOLDER, os.path.splitext(project.filename)[0]) if project.filename else None
            components = []
            if glb_dir and os.path.isdir(glb_dir):
                for file in os.listdir(glb_dir):
                    if file.endswith(".glb"):
                        parts = file.rsplit("_", 1)
                        if len(parts) == 2 and parts[1].endswith(".glb"):
                            guid = parts[0]
                            comp_type = parts[1].replace(".glb", "")
                            name = comp_type.replace("Ifc", "")
                            components.append(
                                ComponentModel(id=guid, name=name, type=comp_type)
                            )
            project_models.append(
                ProjectModel(id=str(project.id), name=project.name, components=components)
            )
        return project_models
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Projekte: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Abrufen der Projekte: {str(e)}")

# Endpunkt zum Löschen aller Projekte
@app.delete("/delete-projects")
async def delete_all_projects(token: str = Form(...), db: Session = Depends(get_db)):
    """Löscht alle Projekte und Komponenten aus der Datenbank."""
    if token != "delete_all_projects_123":
        raise HTTPException(status_code=403, detail="Ungültiger Token")
    try:
        db.query(Component).delete()
        db.query(Project).delete()
        db.commit()
        return {"message": "Alle Projekte und Komponenten erfolgreich gelöscht"}
    except Exception as e:
        db.rollback()
        logger.error(f"Fehler beim Löschen der Projekte: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Löschen der Projekte: {str(e)}")

# Gesundheitsendpunkt
@app.get("/health")
async def health_check():
    """Überprüft den Status des Servers."""
    return {"status": "healthy", "message": "FastAPI-Server läuft erfolgreich"}