from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import ifcopenshell
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List
import subprocess
from sqlalchemy.sql import text

from api.database import SessionLocal, Project, User

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8000"],  # Added localhost:8000 for compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder configuration
BUCKET_FOLDER = os.path.join("uploads", "ifc-bucket")
GLB_FOLDER = os.path.join("uploads", "glb")
TEMP_FOLDER = os.path.join("uploads", "temp_ifcs")
IFC_FILES_FOLDER = os.path.join("uploads", "ifc_files")  # New folder for updated IFC files
os.makedirs(BUCKET_FOLDER, exist_ok=True)
os.makedirs(GLB_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(IFC_FILES_FOLDER, exist_ok=True)  # Create new folder

# IfcConvert configuration
IFCCONVERT_PATH = r"C:\IfcConvert\IfcConvert.exe"  # Adjust to your server's IfcConvert path

# Supported IFC component types
COMPONENT_TYPES = [
    "IfcWall",
    "IfcWindow",
    "IfcSlab",
    "IfcBeam",
    "IfcColumn",
    "IfcDoor",
    "IfcSpace"
]

# Pydantic model for marking reusable components
class ReuseRequest(BaseModel):
    filename: str
    reusable_ids: List[str]

def export_single_element_to_ifc(model, element, output_path):
    """Export a single IFC element to a new IFC file."""
    try:
        new_model = ifcopenshell.file()
        new_model.add(element)
        new_model.write(output_path)
    except Exception as e:
        print(f"❌ Error exporting IFC for element: {str(e)}")
        raise

def convert_ifc_components_to_glb(ifc_path, output_glb_dir):
    """Convert IFC components to GLB files using IfcConvert."""
    try:
        model = ifcopenshell.open(ifc_path)
        total = 0
        errors = []

        for comp_type in COMPONENT_TYPES:
            elements = model.by_type(comp_type)
            print(f"🔸 {comp_type}: {len(elements)} elements found")

            for element in elements:
                guid = element.GlobalId
                glb_filename = f"{guid}_{comp_type}.glb"
                glb_output_path = os.path.join(output_glb_dir, glb_filename)
                temp_ifc_path = os.path.join(TEMP_FOLDER, f"{guid}.ifc")

                # Export single element to temporary IFC
                try:
                    export_single_element_to_ifc(model, element, temp_ifc_path)
                except Exception as e:
                    print(f"❌ Error exporting IFC for {guid}: {str(e)}")
                    errors.append(guid)
                    continue

                # Run IfcConvert to generate GLB
                command = [
                    IFCCONVERT_PATH,
                    temp_ifc_path,
                    glb_output_path,
                    "--use-element-guids"
                ]

                try:
                    result = subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    if os.path.exists(glb_output_path):
                        print(f"✅ {glb_filename} generated")
                        total += 1
                    else:
                        print(f"⚠️ {glb_filename} not created")
                        errors.append(guid)
                except subprocess.CalledProcessError as e:
                    print(f"❌ Error converting {guid}: {e.stderr}")
                    errors.append(guid)
                except Exception as e:
                    print(f"❌ Unexpected error for {guid}: {str(e)}")
                    errors.append(guid)
                finally:
                    # Clean up temporary IFC file
                    if os.path.exists(temp_ifc_path):
                        try:
                            os.remove(temp_ifc_path)
                        except Exception as e:
                            print(f"⚠️ Failed to delete {temp_ifc_path}: {str(e)}")

        print("\n==== Conversion Summary ====")
        print(f"🔧 GLB files created: {total}")
        if errors:
            print(f"⚠️ Failed components: {len(errors)}")
            for guid in errors:
                print(f" - {guid}")
        else:
            print("✅ All components converted successfully")
        return total, errors
    except Exception as e:
        print(f"❌ Error in convert_ifc_components_to_glb: {str(e)}")
        raise

def update_ifc_reuse(filename: str, reusable_ids: List[str]) -> str:
    """Update IFC file to mark specified elements as reusable."""
    ifc_path = os.path.join(IFC_FILES_FOLDER, filename)
    if not os.path.exists(ifc_path):
        raise FileNotFoundError(f"File {filename} not found at {ifc_path}")

    try:
        ifc_file = ifcopenshell.open(ifc_path)
        for global_id in reusable_ids:
            element = ifc_file.by_guid(global_id)
            if element:
                # Add or update Pset_Reuse
                pset = ifcopenshell.util.element.get_psets(element, qto=False).get("Pset_Reuse")
                if not pset:
                    pset = ifcopenshell.api.run("pset.add_pset", ifc_file, product=element, name="Pset_Reuse")
                ifcopenshell.api.run("pset.edit_pset", ifc_file, pset=pset, properties={"Reusable": True})
            else:
                print(f"⚠️ No element with GlobalId {global_id} found.")

        # Save the updated file
        new_filename = f"updated_{filename}"
        new_path = os.path.join(IFC_FILES_FOLDER, new_filename)
        ifc_file.write(new_path)
        return new_filename
    except Exception as e:
        print(f"❌ Error updating IFC file: {str(e)}")
        raise

@app.post("/upload")
async def upload_ifc_file(
    file: UploadFile = File(...),
    projectName: str = Form(...),
    location: str = Form(...)
):
    try:
        # Save uploaded IFC file
        file_path = os.path.join(BUCKET_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Copy to IFC_FILES_FOLDER for reuse functionality
        ifc_files_path = os.path.join(IFC_FILES_FOLDER, file.filename)
        shutil.copy(file_path, ifc_files_path)

        # Parse IFC for summary
        model = ifcopenshell.open(file_path)
        print("[DEBUG] IFC Types:")
        for t in COMPONENT_TYPES:
            print(f"{t}: {len(model.by_type(t))}")

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

        # Database logic
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(id="mock-user-id").first()
            if not user:
                user = User(
                    id="mock-user-id",
                    name="Mock User",
                    email="mock@example.com",
                    password_hash="hash",
                    created_at=datetime.utcnow()
                )
                db.add(user)
                db.commit()

            project = Project(
                user_id="mock-user-id",
                name=projectName,
                description="Uploaded via form",
                location=location,
                filename=file.filename
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        finally:
            db.close()

        # Convert IFC components to GLB
        project_glb_dir = os.path.join(GLB_FOLDER, os.path.splitext(file.filename)[0])
        os.makedirs(project_glb_dir, exist_ok=True)
        print(f"[INFO] Exporting components to {project_glb_dir}")
        total, errors = convert_ifc_components_to_glb(file_path, project_glb_dir)

        # Include conversion results in response
        summary["glb_files_created"] = total
        summary["failed_components"] = errors

        return {
            "message": "IFC file uploaded, parsed, and components converted to GLB successfully",
            "data": summary
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/components/{component_id}/glb")
def serve_glb(component_id: str):
    try:
        for root, _, files in os.walk(GLB_FOLDER):
            for file in files:
                if file.startswith(component_id) and file.endswith(".glb"):
                    return FileResponse(os.path.join(root, file), media_type="model/gltf-binary")
        raise HTTPException(status_code=404, detail="GLB not found")
    except Exception as e:
        print(f"❌ Error serving GLB for {component_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving GLB: {str(e)}")

class Component(BaseModel):
    id: str = Field(...)
    name: str
    type: str

class ProjectModel(BaseModel):
    id: str
    name: str
    components: List[Component] = []

@app.get("/projects/")
def get_projects():
    try:
        db = SessionLocal()
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
                                    Component(
                                        id=guid,
                                        name=name,
                                        type=comp_type
                                    )
                                )

                project_models.append(
                    ProjectModel(
                        id=str(project.id),
                        name=project.name,
                        components=components
                    )
                )
            return project_models
        finally:
            db.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

@app.delete("/delete-projects")
async def delete_all_projects(token: str = Form(...)):
    """Delete all projects and their associated components from the database."""
    if token != "delete_all_projects_123":
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM components"))
            db.query(Project).delete()
            db.commit()
            return {"message": "All projects and components deleted successfully"}
        finally:
            db.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting projects: {str(e)}")

@app.post("/mark_reusable/")
async def mark_reusable(request: ReuseRequest):
    """Mark specified IFC elements as reusable and update the IFC file."""
    try:
        new_filename = update_ifc_reuse(request.filename, request.reusable_ids)
        return {"status": "success", "new_filename": new_filename}
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "message": str(e)})
    except Exception as e:
        print(f"❌ Error in mark_reusable: {str(e)}")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Error processing request: {str(e)}"})

