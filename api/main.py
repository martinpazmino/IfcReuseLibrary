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
        component_types = ["IfcWall", "IfcWindow", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcSpace"]
        parsed_components = []

        for comp_type in component_types:
            for item in model.by_type(comp_type):
                parsed_components.append({
                    "name": item.Name or f"Unnamed {comp_type}",
                    "type": comp_type
                })

        # 🔹 Save project and components
        db = SessionLocal()

        # Mock user logic (keep for now)
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

        # 🔹 Save components
        for comp in parsed_components:
            db.add(Component(
                name=comp["name"],
                type=comp["type"],
                project_id=project.id
            ))

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
