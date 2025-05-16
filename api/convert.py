import os
import subprocess
import ifcopenshell
from api.database import SessionLocal, Component

# Carpetas y ejecutable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
MODEL_FOLDER = os.path.join(ROOT_DIR, "static", "models")
TEMP_FOLDER = os.path.join(ROOT_DIR, "temp_ifcs")
IFCCONVERT_PATH = r"C:\IfcConvert\IfcConvert.exe"  # ⚠️ Ajusta si es diferente

os.makedirs(MODEL_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

def export_single_element(model, element, output_path):
    new_model = ifcopenshell.file()
    new_model.add(element)
    new_model.write(output_path)

def convert_ifc_components(file_path: str, location: str, project_id: str):
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

    db = SessionLocal()
    parsed_components = []
    obj_files = []

    try:
        for comp_type, (category, subcategory) in component_types.items():
            elements = model.by_type(comp_type)
            print(f"🔍 {comp_type}: {len(elements)} elementos")
            for item in elements:
                guid = item.GlobalId
                name = item.Name or f"Unnamed {comp_type}"

                # Material
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

                # Exportar a IFC temporal
                temp_ifc_path = os.path.join(TEMP_FOLDER, f"{guid}.ifc")
                export_single_element(model, item, temp_ifc_path)

                # Convertir a OBJ
                obj_filename = f"{guid}_{comp_type}.obj"
                obj_output_path = os.path.join(MODEL_FOLDER, obj_filename)

                try:
                    subprocess.run([
                        IFCCONVERT_PATH,
                        temp_ifc_path,
                        obj_output_path,
                        "--use-element-guids"
                    ], capture_output=True, text=True, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"❌ Error al convertir {guid}: {e.stderr}")
                    continue

                # Guardar componente en DB con el project_id correcto
                component = Component(
                    project_id=project_id,
                    name=name,
                    category=category,
                    subcategory=subcategory,
                    type=comp_type,
                    material=material,
                    location=location,
                    reuse_flag=True,
                    dimensions={},
                    quantity=1,
                    extra_metadata={},
                    preview_url=""
                )
                db.add(component)
                db.flush()

                # Estructura de respuesta
                parsed_components.append({
                    "id": component.id,
                    "name": name,
                    "type": comp_type,
                    "guid": guid,
                    "material": material,
                    "category": category,
                    "subcategory": subcategory,
                    "location": location
                })

                obj_files.append({
                    "name": name,
                    "type": comp_type,
                    "guid": guid,
                    "obj_url": f"/static/models/{obj_filename}"
                })

        db.commit()

    finally:
        db.close()

    return parsed_components, obj_files

# 🧪 Modo standalone desde consola
if __name__ == "__main__":
    import sys
    from uuid import uuid4

    if len(sys.argv) < 2:
        print("⚠️  Uso: python convert.py archivo.ifc")
        sys.exit(1)

    file_path = sys.argv[1]
    location = "Manual"
    project_id = str(uuid4())  # Dummy project for standalone run

    print(f"📂 Procesando IFC: {file_path}")
    components, obj_files = convert_ifc_components(file_path, location, project_id)

    print(f"\n✅ Componentes convertidos: {len(components)}")
    for c in components:
        print(f" - {c['type']} ({c['guid']})")

    print(f"\n📦 OBJ generados: {len(obj_files)}")
    for o in obj_files:
        print(f" → {o['obj_url']}")
