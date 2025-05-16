# export_glb.py

import os
import ifcopenshell
import ifcopenshell.geom
import trimesh

def export_component_glb(ifc_path, output_dir):
    print(f"[INFO] Processing {ifc_path}")
    os.makedirs(output_dir, exist_ok=True)
    model = ifcopenshell.open(ifc_path)

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    types = ["IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", "IfcWindow"]
    all_elements = []
    for t in types:
        elems = model.by_type(t)
        print(f"[DEBUG] {t}: {len(elems)}")
        all_elements.extend(elems)

    for entity in all_elements:
        try:
            shape = ifcopenshell.geom.create_shape(settings, entity)
            geom = shape.geometry
            mesh = trimesh.Trimesh(vertices=geom.verts, faces=geom.faces)
            out_path = os.path.join(output_dir, f"{entity.GlobalId}.glb")
            mesh.export(out_path)
            print(f"[GLB] Exported: {out_path}")
        except Exception as e:
            print(f"[WARN] {entity.GlobalId}: {e}")

# Run it
export_component_glb(
    "/data/uploads/ifc-bucket/AC20-FZK-Haus.ifc",
    "/data/uploads/glb/docker-test"
)
