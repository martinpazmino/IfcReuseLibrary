import ifcopenshell

def parse_ifc_components(file_path):
    ifc = ifcopenshell.open(file_path)
    walls = ifc.by_type("IfcWall")
    return [{"name": w.Name or "Unnamed", "type": "IfcWall"} for w in walls]
