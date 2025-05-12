from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil, os, uuid
import ifcopenshell
from datetime import datetime
from .database import SessionLocal, User, Project, Component
from api.database import SessionLocal, Project, User  # Add User model

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080"],  # ✅ Corrected key
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_FOLDER = os.path.join("uploads", "ifc-bucket")
os.makedirs(BUCKET_FOLDER, exist_ok=True)


@app.post("/upload")
async def upload_ifc_file(
    file: UploadFile = File(...),
    projectName: str = Form(...),
    location: str = Form(...)
):
    try:
        # 🔹 Save file
        os.makedirs(BUCKET_FOLDER, exist_ok=True)
        file_id = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(BUCKET_FOLDER, file_id)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 🔹 Parse IFC components
        model = ifcopenshell.open(file_path)
        component_types = {
            "IfcWall": ("Architectural", "Wall"),
            "IfcWindow": ("Architectural", "Window"),
            "IfcSlab": ("Structural", "Slab"),
            "IfcBeam": ("Structural", "Beam"),
            "IfcColumn": ("Structural", "Column"),
            "IfcDoor": ("Architectural", "Door"),
            "IfcSpace": ("MEP", "Space")
        }

        parsed_components = []

        for comp_type, (category, subcategory) in component_types.items():
            for item in model.by_type(comp_type):
                name = item.Name or f"Unnamed {comp_type}"

                # Try to extract material
                material = "Unknown"
                rels = item.HasAssociations or []
                for rel in rels:
                    if rel.is_a("IfcRelAssociatesMaterial") and hasattr(rel, "RelatingMaterial"):
                        mat = rel.RelatingMaterial
                        if mat.is_a("IfcMaterial"):
                            material = mat.Name
                        elif mat.is_a("IfcMaterialLayerSetUsage"):
                            layer_set = mat.ForLayerSet
                            if layer_set and layer_set.MaterialLayers:
                                material = layer_set.MaterialLayers[0].Material.Name
                        break

                parsed_components.append({
                    "name": name,
                    "type": comp_type,
                    "category": category,
                    "subcategory": subcategory,
                    "material": material,
                    "location": location,
                    "reuse_flag": True
                })

        # 🔹 Save project and components
        # Still inside the outer try block after project creation

        db = SessionLocal()  # Open DB session

        # 🔹 Mock user logic
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

        # 🔹 Save project
        project = Project(
            user_id="mock-user-id",
            name=projectName,
            description="Uploaded via form",
            location=location
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # 🔹 Save components
        for comp_type, (category, subcategory) in component_types.items():
            for item in model.by_type(comp_type):
                name = item.Name or f"Unnamed {comp_type}"

                # Extract material
                material = "Unknown"
                rels = item.HasAssociations or []
                for rel in rels:
                    if rel.is_a("IfcRelAssociatesMaterial") and hasattr(rel, "RelatingMaterial"):
                        mat = rel.RelatingMaterial
                        if mat.is_a("IfcMaterial"):
                            material = mat.Name
                        elif mat.is_a("IfcMaterialLayerSetUsage"):
                            layer_set = mat.ForLayerSet
                            if layer_set and layer_set.MaterialLayers:
                                material = layer_set.MaterialLayers[0].Material.Name
                        break

                # Add component
                component = Component(
                    project_id=project.id,
                    name=name,
                    category=category,
                    subcategory=subcategory,
                    material=material,
                    location=location,
                    reuse_flag=True,
                    dimensions={},  # placeholder
                    quantity=1,
                    extra_metadata={},
                    preview_url=""
                )
                db.add(component)

        # ✅ Commit once at the end
        db.commit()
        db.close()

        return {
            "message": "IFC file uploaded and components stored",
            "data": {
                "project_id": project.id,
                "project_name": project.name,
                "components": parsed_components
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
@app.get("/projects/")
def get_projects():
    db = SessionLocal()
    projects = db.query(Project).all()
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "location": p.location,
            "components": [{"name": c.name, "type": c.type} for c in p.components]
        })
    db.close()
    return result

@app.get("/uploads/ifc-bucket")
def serve_file(filename: str):
    file_path = os.path.join("uploads", "ifc-bucket", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}
