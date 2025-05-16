from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import ifcopenshell
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List

from api.database import SessionLocal, Project, User  # Add User model
from api.extract_glb import export_component_glb  # <-- Import extractor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_FOLDER = os.path.join("uploads", "ifc-bucket")
GLB_FOLDER = os.path.join("uploads", "glb")
os.makedirs(BUCKET_FOLDER, exist_ok=True)
os.makedirs(GLB_FOLDER, exist_ok=True)

@app.post("/upload")
async def upload_ifc_file(
    file: UploadFile = File(...),
    projectName: str = Form(...),
    location: str = Form(...)
):
    try:
        # Save file
        file_path = os.path.join(BUCKET_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse IFC
        model = ifcopenshell.open(file_path)
        print("[DEBUG] IFC Types:")
        for t in ["IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcWindow", "IfcBuildingElement"]:
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

        # DB logic
        db = SessionLocal()

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
            location=location
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        db.close()

        # 🔹 Export GLBs
        project_glb_dir = os.path.join(GLB_FOLDER, os.path.splitext(file.filename)[0])
        print(f"[INFO] Exporting components to {project_glb_dir}")
        export_component_glb(file_path, project_glb_dir)

        return {
            "message": "IFC file uploaded and parsed successfully",
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

projects = [
    ProjectModel(
        id="1",
        name="Project Alpha",
        components=[
            Component(id="comp1", name="Beam", type="Structural"),
            Component(id="comp2", name="Column", type="Structural")
        ]
    ),
    ProjectModel(
        id="2",
        name="Project Beta",
        components=[
            Component(id="comp3", name="Wall", type="Architectural")
        ]
    )
]

@app.get("/projects/")
def get_projects():
    return projects
