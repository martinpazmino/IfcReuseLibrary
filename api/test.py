# export_glb_manual_test.py

import os
import ifcopenshell
import ifcopenshell.geom
import trimesh
import sys
sys.path.insert(0, r"C:\Users\HP\OneDrive\Documentos\martin\martin\Uni\4 semester\P3\IFC Reuse Library\IfcOpenshell\win\install-ifcopenshell.bat")

def export_component_glb(ifc_path: str, output_dir: str):
    print(f"[INFO] Exporting GLBs to: {output_dir}")
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
            elems = model.by_type(t)
            print(f"[DEBUG] {t}: {len(elems)}")
            all_elements.extend(elems)

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


if __name__ == "__main__":
    ifc_file = r"C:\Users\HP\OneDrive\Documentos\martin\martin\Uni\4 semester\P3\IFC Reuse Library\uploads\ifc-bucket\AC20-FZK-Haus.ifc"

    output_dir = r"C:\Users\HP\OneDrive\Documentos\martin\martin\Uni\4 semester\P3\IFC Reuse Library\uploads\glb\AC20-FZK-Haus-manual"


    if not os.path.isfile(ifc_file):
        print(f"[ERROR] IFC file not found at: {ifc_file}")
    else:
        export_component_glb(ifc_file, output_dir)
