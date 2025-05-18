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
import uuid
import re

from api.database import SessionLocal, Project, User

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder configuration
BUCKET_FOLDER = os.path.join("uploads", "ifc-bucket")
GLB_FOLDER = os.path.join("uploads", "glb")
TEMP_FOLDER = os.path.join("uploads", "temp_ifcs")
os.makedirs(BUCKET_FOLDER, exist_ok=True)
os.makedirs(GLB_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

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

def export_single_element_to_ifc(model, element, output_path):
    """Export a single IFC element to a new IFC file."""
    new_model = ifcopenshell.file()
    new_model.add(element)
    new_model.write(output_path)

def convert_ifc_components_to_glb(ifc_path, output_glb_dir):
    """Convert IFC components to GLB files using IfcConvert."""
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
        # Generate a valid UUID for the user
        mock_user_id = str(uuid.uuid4())
        # Validate that mock_user_id is a valid UUID
        uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        if not uuid_pattern.match(mock_user_id):
            raise ValueError(f"Generated user_id {mock_user_id} is not a valid UUID")

        user = db.query(User).filter_by(id=mock_user_id).first()
        if not user:
            user = User(
                id=mock_user_id,
                name="Mock User",
                email="mock@example.com",
                password_hash="hash",
                created_at=datetime.utcnow()
            )
            db.add(user)
            db.commit()

        # Generate a valid UUID for the project
        project_id = str(uuid.uuid4())
        if not uuid_pattern.match(project_id):
            raise ValueError(f"Generated project_id {project_id} is not a valid UUID")

        project = Project(
            id=project_id,
            user_id=mock_user_id,
            name=projectName,
            description="Uploaded via form",
            location=location,
            filename=file.filename
        )
        db.add(project)
        db.commit()
        db.refresh(project)
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
    for root, _, files in os.walk(GLB_FOLDER):
        for file in files:
            if file.startswith(component_id) and file.endswith(".glb"):
                return FileResponse(os.path.join(root, file), media_type="model/gltf-binary")
    raise HTTPException(status_code=404, detail="GLB not found")

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
        projects = db.query(Project).all()
        db.close()

        project_models = []
        for project in projects:
            # Use the stored filename to find the GLB folder
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

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

@app.delete("/delete-projects")
async def delete_all_projects(token: str = Form(...)):
    """Delete all projects and their associated components from the database."""
    # Simple token-based authentication for development (replace with proper auth in production)
    if token != "delete_all_projects_123":
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        db = SessionLocal()
        # Delete all components to satisfy foreign key constraint
        db.execute(text("DELETE FROM components"))
        # Delete all projects
        db.query(Project).delete()
        db.commit()
        db.close()

        # Optional: Clean up GLB and IFC folders (uncomment if desired)
        # if os.path.exists(GLB_FOLDER):
        #     shutil.rmtree(GLB_FOLDER)
        # if os.path.exists(BUCKET_FOLDER):
        #     shutil.rmtree(BUCKET_FOLDER)
        # os.makedirs(GLB_FOLDER, exist_ok=True)
        # os.makedirs(BUCKET_FOLDER, exist_ok=True)

        return {"message": "All projects and components deleted successfully"}

    except Exception as e:
        db.rollback()
        db.close()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting projects: {str(e)}")