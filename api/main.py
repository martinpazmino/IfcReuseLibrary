from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import shutil
import ifcopenshell
from datetime import datetime

from database import SessionLocal, Project, User  # Add User model

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
        # Save file
        file_path = os.path.join(BUCKET_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse IFC
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

        # DB logic
        db = SessionLocal()

        # ✅ Ensure mock-user exists
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

        # Save project
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

        return {
            "message": "IFC file uploaded and parsed successfully",
            "data": summary
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
