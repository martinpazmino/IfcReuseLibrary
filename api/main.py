from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import shutil
import ifcopenshell

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    # Save IFC to disk
    file_path = os.path.join(BUCKET_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse the file (same as before)
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

    # Save Project to DB with location
    db = SessionLocal()
    project = Project(
        user_id="mock-user-id",  # You can change this later
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
        return JSONResponse(status_code=500, content={"error": str(e)})
