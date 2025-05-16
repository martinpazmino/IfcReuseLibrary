import ifcopenshell

# Load IFC model
ifc_file = ifcopenshell.open("AC20-FZK-Haus.ifc")

# Get all IfcWall elements
walls = ifc_file.by_type("IfcWall")

# Iterate over each wall and extract GrossVolume
for wall in walls:
    gross_volume = None
    # Check property definitions
    for rel in wall.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            prop_set = rel.RelatingPropertyDefinition
            if prop_set.is_a("IfcElementQuantity"):
                for quantity in prop_set.Quantities:
                    if quantity.is_a("IfcQuantityVolume") and quantity.Name == "NetVolume":
                        gross_volume = quantity.VolumeValue
                        break
    # Output result
    print(f"Wall: {wall.GlobalId}, Gross Volume: {gross_volume} m³")


