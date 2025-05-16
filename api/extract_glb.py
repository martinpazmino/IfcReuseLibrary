# api/extract_glb.py

import ifcopenshell
import ifcopenshell.geom
import trimesh
import os

def export_component_glb(ifc_path: str, output_dir: str):
    print(f"[INFO] Exporting GLBs to {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    try:
        model = ifcopenshell.open(ifc_path)
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        settings.set(settings.DISABLE_OPENING_SUBTRACTIONS, True)
        settings.set(settings.USE_PYTHON_OPENCASCADE, True)

        types = ["IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcWindow"]
        all_elements = []
        for t in types:
            found = model.by_type(t)
            print(f"[DEBUG] {t}: {len(found)}")
            all_elements.extend(found)

        for entity in all_elements:
            try:
                shape = ifcopenshell.geom.create_shape(settings, entity)
                geometry = shape.geometry
                mesh = trimesh.Trimesh(vertices=geometry.verts, faces=geometry.faces)
                glb_path = os.path.join(output_dir, f"{entity.GlobalId}.glb")
                mesh.export(glb_path)
                print(f"[GLB] Exported: {glb_path}")
            except Exception as e:
                print(f"[WARN] Failed to export {entity.GlobalId}: {e}")

    except Exception as e:
        print(f"[ERROR] Unable to process IFC file: {e}")
