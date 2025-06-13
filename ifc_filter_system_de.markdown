# Aufbau eines dynamischen Filtersystems für IFC-Dokumente

Um ein dynamisches Filtersystem für IFC-Dokumente (Industry Foundation Classes) zu erstellen, die der gleichen Struktur wie die bereitgestellten Beispiele folgen, aber unterschiedliche Inhalte enthalten (z. B. andere Materialien, Abmessungen oder Attribute), muss das System flexibel genug sein, um vielfältige IFC-Daten zu verarbeiten und gleichzeitig mit dem bestehenden Django-Backend und der Frontend-Einrichtung kompatibel zu bleiben. Das Filtersystem soll Kategorien, Unterkategorien, Eigenschaften und Eigenschaftswerte dynamisch aus den hochgeladenen IFC-Dokumenten extrahieren, diese in der Datenbank speichern und sie für die Filterung im Frontend verfügbar machen. Im Folgenden beschreibe ich, wie das Filtersystem angepasst werden kann, um solche IFC-Dokumente zu verarbeiten, mit Fokus auf die Datenbank, die Backend-API und die Frontend-Integration.

## Wichtige Überlegungen
- **IFC-Struktur**: Die bereitgestellten IFC-Elemente haben eine konsistente Struktur mit Feldern wie `type`, `Name`, `ObjectType`, `materials`, `storey`, `OverallHeight`, `OverallWidth` und `GlobalId`. Neue Uploads können jedoch andere IFC-Typen (z. B. `IfcBeam`, `IfcColumn`), Materialien (z. B. „Aluminium“, „Ziegel“) oder zusätzliche Eigenschaften (z. B. `PredefinedType`, `ThermalTransmittance`) enthalten.
- **Dynamische Kategorisierung**: Das Filtersystem muss IFC-Typen dynamisch Hauptkategorien und Unterkategorien zuordnen, Eigenschaften aus Feldern wie `materials`, `Name` oder benutzerdefinierten IFC-Eigenschaften extrahieren und unterschiedliche Eigenschaftswerte ohne Festkodierung verarbeiten.
- **Datenbankintegration**: Verwenden Sie die bestehenden Django-Modelle (`MainCategory`, `SubCategory`, `Component`), wobei das `properties`-JSON-Feld dynamische Attribute speichert.
- **Frontend**: Das Frontend (`catalog.html`) soll weiterhin API-Aufrufe nutzen, um Dropdowns zu füllen, ohne Änderungen, wenn das Backend die korrekten Daten liefert.
- **Upload-Verarbeitung**: Verarbeiten Sie hochgeladene IFC-Dateien, um relevante Daten zu extrahieren und zu speichern, und aktualisieren Sie die Filteroptionen automatisch.

## Ansatz zum Aufbau des Filtersystems
Das Filtersystem besteht aus vier Dropdowns (Hauptkategorie, Unterkategorie, Eigenschaft, Eigenschaftswerte), die dynamisch den Inhalt der hochgeladenen IFC-Dokumente widerspiegeln. Hier ist der Aufbau:

### 1. Datenbankschema
Die bestehenden Modelle (`MainCategory`, `SubCategory`, `Component`) sind ausreichend, aber wir müssen sicherstellen, dass sie dynamische IFC-Daten verarbeiten können:

- **MainCategory**: Bleibt unverändert mit vordefinierten Kategorien (z. B. Tragwerkselemente, Ausbauelemente, Dachelemente).
- **SubCategory**: Weisen Sie IFC-Typen dynamisch Unterkategorien zu, basierend auf `type` (z. B. `IfcWall` → „Wände“). Fügen Sie neue Unterkategorien für unbekannte IFC-Typen hinzu.
- **Component**: Speichern Sie jedes IFC-Element mit seinem `properties`-JSON-Feld, das aus Feldern wie `materials`, `OverallHeight`, `OverallWidth`, `storey` und geparstem `Name` oder `ObjectType` gefüllt wird.
- **Neues Modell (optional)**: Fügen Sie ein `Property`-Modell hinzu, um gültige Eigenschaften pro Unterkategorie vorzudefinieren, was die Abfrageleistung und Validierung verbessert.

**Geändertes `core/models.py`**:
```python
from django.db import models
from jsonfield import JSONField

class MainCategory(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100)
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE, related_name='subcategories')
    ifc_types = models.JSONField(default=list)  # Speichert IFC-Typen (z. B. ["IfcWall", "IfcCurtainWall"])

    def __str__(self):
        return self.name

class Component(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    main_category = models.ForeignKey(MainCategory, on_delete=models.CASCADE)
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE)
    properties = JSONField()  # z. B. {"material": "Holz", "abmessungen": "1200x2000mm", ...}
    fragment_id = models.CharField(max_length=100)  # Aus IFC fragmentID
    model_uuid = models.CharField(max_length=100)  # Aus IFC modelUUID

    def __str__(self):
        return self.name
```

**Änderungen**:
- `ifc_types` zu `SubCategory` hinzugefügt, um IFC-Typen Unterkategorien zuzuordnen.
- `fragment_id` und `model_uuid` zu `Component` hinzugefügt, um IFC-spezifische Kennungen für die Darstellung zu speichern.

**Migration**:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Zuordnung von IFC-Typen zu Kategorien
Erstellen Sie eine Zuordnung, um IFC-Typen dynamisch Hauptkategorien und Unterkategorien zuzuweisen. Diese kann in der Datenbank oder einer Konfigurationsdatei gespeichert werden. Hier ist eine vorgeschlagene Zuordnung basierend auf gängigen IFC-Typen und den bereitgestellten Daten:

```python
IFC_TYPE_MAPPING = {
    'IfcWall': {'main_category': 'ausbauelemente', 'sub_category': 'wande'},
    'IfcWindow': {'main_category': 'ausbauelemente', 'sub_category': 'fenster'},
    'IfcDoor': {'main_category': 'ausbauelemente', 'sub_category': 'turen'},
    'IfcSlab': {'main_category': 'dachelemente', 'sub_category': 'dachdecken'},
    'IfcBuildingElementProxy': {'main_category': 'ausbauelemente', 'sub_category': 'sonstige_bauteile'},
    # Weitere Zuordnungen für andere IFC-Typen
    'IfcBeam': {'main_category': 'tragwerkselemente', 'sub_category': 'holzbalken'},
    'IfcColumn': {'main_category': 'tragwerkselemente', 'sub_category': 'stutzen'},
    'IfcRoof': {'main_category': 'dachelemente', 'sub_category': 'dachdecken'},
}
```

**Initialisierung**:
Aktualisieren Sie den Befehl `populate_categories`, um `ifc_types` einzuschließen.

**Geändertes `core/management/commands/populate_categories.py`**:
```python
from django.core.management.base import BaseCommand
from core.models import MainCategory, SubCategory

class Command(BaseCommand):
    help = 'Initiale Kategorien und Unterkategorien füllen'

    def handle(self, *args, **kwargs):
        categories = [
            {
                'id': 'tragwerkselemente', 'name': 'Tragwerkselemente',
                'subcategories': [
                    {'id': 'holzbalken', 'name': 'Holzbalken', 'ifc_types': ['IfcBeam']},
                    {'id': 'stahltrager', 'name': 'Stahlträger', 'ifc_types': []},
                    {'id': 'stutzen', 'name': 'Stützen', 'ifc_types': ['IfcColumn']},
                    {'id': 'betonfertigteile', 'name': 'Betonfertigteile', 'ifc_types': []},
                ]
            },
            {
                'id': 'ausbauelemente', 'name': 'Ausbauelemente',
                'subcategories': [
                    {'id': 'fenster', 'name': 'Fenster', 'ifc_types': ['IfcWindow']},
                    {'id': 'turen', 'name': 'Türen', 'ifc_types': ['IfcDoor']},
                    {'id': 'bodenbelage', 'name': 'Bodenbeläge', 'ifc_types': []},
                    {'id': 'wandverkleidungen', 'name': 'Wandverkleidungen', 'ifc_types': []},
                    {'id': 'wande', 'name': 'Wände', 'ifc_types': ['IfcWall', 'IfcCurtainWall']},
                    {'id': 'sonstige_bauteile', 'name': 'Sonstige Bauteile', 'ifc_types': ['IfcBuildingElementProxy']},
                ]
            },
            {
                'id': 'technische_gebaudeausrustung', 'name': 'Technische Gebäudeausrüstung',
                'subcategories': [
                    {'id': 'heizungssysteme', 'name': 'Heizungssysteme', 'ifc_types': []},
                    {'id': 'lueftungssysteme', 'name': 'Lüftungssysteme', 'ifc_types': []},
                    {'id': 'sanitarsysteme', 'name': 'Sanitärsysteme', 'ifc_types': []},
                    {'id': 'elektroinstallationen', 'name': 'Elektroinstallationen', 'ifc_types': []},
                ]
            },
            {
                'id': 'dachelemente', 'name': 'Dachelemente',
                'subcategories': [
                    {'id': 'dachziegel', 'name': 'Dachziegel', 'ifc_types': []},
                    {'id': 'dachplatten', 'name': 'Dachplatten', 'ifc_types': []},
                    {'id': 'dachfenster', 'name': 'Dachfenster', 'ifc_types': []},
                    {'id': 'dachisolierung', 'name': 'Dachisolierung', 'ifc_types': []},
                    {'id': 'dachdecken', 'name': 'Dachdecken', 'ifc_types': ['IfcSlab', 'IfcRoof']},
                ]
            },
            {
                'id': 'treppen', 'name': 'Treppen',
                'subcategories': [
                    {'id': 'treppenstufen', 'name': 'Treppenstufen', 'ifc_types': []},
                    {'id': 'gelander', 'name': 'Geländer', 'ifc_types': []},
                    {'id': 'treppenkonstruktion', 'name': 'Treppenkonstruktion', 'ifc_types': ['IfcStair']},
                ]
            },
        ]

        for category in categories:
            main_cat, _ = MainCategory.objects.get_or_create(id=category['id'], name=category['name'])
            for sub_cat in category['subcategories']:
                SubCategory.objects.get_or_create(
                    id=sub_cat['id'],
                    name=sub_cat['name'],
                    main_category=main_cat,
                    defaults={'ifc_types': sub_cat['ifc_types']}
                )
        
        self.stdout.write(self.style.SUCCESS('Kategorien und Unterkategorien erfolgreich gefüllt'))
```

**Ausführen**:
```bash
python manage.py populate_categories
```

### 3. Verarbeitung hochgeladener IFC-Dateien
Wenn eine IFC-Datei hochgeladen wird, parsen Sie sie, um Elemente zu extrahieren und als `Component`-Instanzen zu speichern. Verwenden Sie `ifcopenshell`, um IFC-Dateien zu verarbeiten.

**Installation**:
```bash
pip install ifcopenshell
```

**Upload-Ansicht**:
Ändern Sie die `upload_component`-Ansicht, um IFC-Dateien zu verarbeiten. Es wird angenommen, dass Uploads als Dateien an einen Endpunkt (z. B. `/api/upload-ifc`) gesendet werden.

**Geändertes `core/views.py` (zum bestehenden hinzufügen)**:
```python
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models import MainCategory, SubCategory, Component
from core.serializers import ComponentSerializer
import ifcopenshell
from django.core.files.storage import FileSystemStorage
import uuid

@api_view(['POST'])
def upload_ifc(request):
    try:
        ifc_file = request.FILES['ifc_file']
        fs = FileSystemStorage()
        filename = fs.save(ifc_file.name, ifc_file)
        file_path = fs.path(filename)

        # IFC-Datei parsen
        ifc = ifcopenshell.open(file_path)
        elements = ifc.by_type(['IfcWall', 'IfcWindow', 'IfcDoor', 'IfcSlab', 'IfcBuildingElementProxy', 'IfcBeam', 'IfcColumn', 'IfcRoof', 'IfcStair'])
        
        IFC_TYPE_MAPPING = {
            'IfcWall': {'main_category': 'ausbauelemente', 'sub_category': 'wande'},
            'IfcWindow': {'main_category': 'ausbauelemente', 'sub_category': 'fenster'},
            'IfcDoor': {'main_category': 'ausbauelemente', 'sub_category': 'turen'},
            'IfcSlab': {'main_category': 'dachelemente', 'sub_category': 'dachdecken'},
            'IfcBuildingElementProxy': {'main_category': 'ausbauelemente', 'sub_category': 'sonstige_bauteile'},
            'IfcBeam': {'main_category': 'tragwerkselemente', 'sub_category': 'holzbalken'},
            'IfcColumn': {'main_category': 'tragwerkselemente', 'sub_category': 'stutzen'},
            'IfcRoof': {'main_category': 'dachelemente', 'sub_category': 'dachdecken'},
            'IfcStair': {'main_category': 'treppen', 'sub_category': 'treppenkonstruktion'},
        }

        components = []
        for element in elements:
            ifc_type = element.is_a()
            mapping = IFC_TYPE_MAPPING.get(ifc_type, {'main_category': 'ausbauelemente', 'sub_category': 'sonstige_bauteile'})
            main_cat = MainCategory.objects.get(id=mapping['main_category'])
            sub_cat = SubCategory.objects.get(id=mapping['sub_category'])

            # Materialien extrahieren
            materials = []
            for assoc in getattr(element, 'HasAssociations', []):
                if assoc.is_a('IfcMaterial'):
                    materials.append(assoc.Name)
            
            # Abmessungen extrahieren
            dimensions = ''
            if hasattr(element, 'OverallWidth') and hasattr(element, 'OverallHeight'):
                width = getattr(element, 'OverallWidth', None)
                height = getattr(element, 'OverallHeight', None)
                if width and height:
                    dimensions = f"{width}x{height}mm"
            elif 'materials' in element and element.materials and 'thickness' in element.materials[0]:
                dimensions = f"Dicke {element.materials[0]['thickness']}m"

            # Name oder ObjectType für zusätzliche Eigenschaften parsen
            name = element.Name or ''
            object_type = getattr(element, 'ObjectType', '') or ''
            material_from_name = ''
            if 'Wood' in name or 'Wood' in object_type:
                material_from_name = 'Holz'
            elif 'Stone' in name or 'Stone' in object_type:
                material_from_name = 'Stein'
            elif 'Steel' in name or 'Steel' in object_type:
                material_from_name = 'Stahl'

            properties = {
                'material': ', '.join(materials) or material_from_name or 'Unbekannt',
                'abmessungen': dimensions or 'Unbekannt',
                'zustand_schadensfreiheit': 'Gebraucht',  # Standard, könnte aus IFC extrahiert werden
                'storey': element.ContainedInStructure[0].Name if hasattr(element, 'ContainedInStructure') and element.ContainedInStructure else 'Unbekannt',
            }

            # Spezifische Eigenschaften basierend auf Unterkategorie hinzufügen
            if sub_cat.id == 'fenster':
                properties['verglasung'] = 'Doppel' if 'double' in name.lower() else 'Einfach'
            elif sub_cat.id in ['turen', 'wandverkleidungen']:
                properties['oberflachenbehandlung'] = 'Satin' if 'Satin' in str(materials) else 'Unbekannt'
            elif sub_cat.id == 'dachdecken':
                properties['oberflachenbeschaffenheit'] = 'Rau' if 'Beton' in properties['material'] else 'Unbekannt'

            component = Component.objects.create(
                id=str(element.id()),
                name=name,
                main_category=main_cat,
                sub_category=sub_cat,
                properties=properties,
                fragment_id=element.get_info().get('fragmentID', str(uuid.uuid4())),
                model_uuid=element.get_info().get('modelUUID', str(uuid.uuid4())),
            )
            components.append(component)

        serializer = ComponentSerializer(components, many=True)
        # WebSocket-Clients benachrichtigen (falls Channels verwendet wird)
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "components", {"type": "component_update", "message": "update"}
        )
        return Response(serializer.data, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
```

**URL**:
In `core/urls.py` hinzufügen:
```python
path('api/upload-ifc', views.upload_ifc, name='upload-ifc'),
```

### 4. Backend-API
Die bestehenden API-Endpunkte (`main_categories`, `sub_categories`, `properties`, `property_values`, `components`) sind bereits für dynamische Daten ausgelegt. Stellen Sie sicher, dass sie mit dem aktualisierten Schema funktionieren:

- **Hauptkategorien**: Keine Änderung nötig; listet alle `MainCategory`-Objekte auf.
- **Unterkategorien**: Filtern nach `main_category_id`, `ifc_types` im Serializer falls nötig einbeziehen.
- **Eigenschaften**: Dynamisch Schlüssel aus `Component.properties` für die gewählte Hauptkategorie und Unterkategorie extrahieren.
- **Eigenschaftswerte**: Einzigartige Werte für die gewählte Eigenschaft extrahieren, neue Materialien oder Abmessungen verarbeiten.
- **Komponenten**: Komponenten basierend auf den gewählten Filtern filtern, einschließlich neuer Eigenschaften wie `verglasung`.

**Geändertes `core/serializers.py`**:
```python
from rest_framework import serializers
from core.models import MainCategory, SubCategory, Component

class MainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCategory
        fields = ['id', 'name']

class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'ifc_types']

class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = ['id', 'name', 'main_category', 'sub_category', 'properties', 'fragment_id', 'model_uuid']
```

**Bestehendes `core/views.py` (Kompatibilität sicherstellen)**:
```python
# ... andere Importe
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.aggregates import ArrayAgg

@api_view(['GET'])
def main_categories(request):
    categories = MainCategory.objects.all()
    serializer = MainCategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def sub_categories(request):
    main_category = request.GET.get('main_category')
    if not main_category:
        return Response({'error': 'Hauptkategorie erforderlich'}, status=400)
    subcategories = SubCategory.objects.filter(main_category_id=main_category)
    serializer = SubCategorySerializer(subcategories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def properties(request):
    main_category = request.GET.get('main_category')
    sub_category = request.GET.get('sub_category')
    if not (main_category and sub_category):
        return Response({'error': 'Hauptkategorie und Unterkategorie erforderlich'}, status=400)
    
    components = Component.objects.filter(
        main_category_id=main_category,
        sub_category_id=sub_category
    )
    properties = set()
    for component in components:
        properties.update(component.properties.keys())
    return Response([{'id': prop, 'name': prop.replace('_', '/')} for prop in sorted(properties)])

@api_view(['GET'])
def property_values(request):
    main_category = request.GET.get('main_category')
    sub_category = request.GET.get('sub_category')
    property = request.GET.get('property')
    if not (main_category and sub_category and property):
        return Response({'error': 'Hauptkategorie, Unterkategorie und Eigenschaft erforderlich'}, status=400)
    
    values = Component.objects.filter(
        main_category_id=main_category,
        sub_category_id=sub_category
    ).annotate(
        value=KeyTextTransform(property, 'properties')
    ).values('value').distinct()
    values = [v['value'] for v in values if v['value'] is not None]
    return Response(sorted(values))

@api_view(['GET'])
def components(request):
    main_category = request.GET.get('main_category')
    sub_category = request.GET.get('sub_category')
    property = request.GET.get('property')
    value = request.GET.get('value')
    
    query = Q()
    if main_category:
        query &= Q(main_category_id=main_category)
    if sub_category:
        query &= Q(sub_category_id=sub_category)
    if property and value:
        query &= Q(**{f'properties__{property}': value})
    
    components = Component.objects.filter(query)
    serializer = ComponentSerializer(components, many=True)
    return Response(serializer.data)
```

**SQLite-Kompatibilität** (falls kein PostgreSQL verwendet wird):
```python
@api_view(['GET'])
def property_values(request):
    main_category = request.GET.get('main_category')
    sub_category = request.GET.get('sub_category')
    property = request.GET.get('property')
    if not (main_category and sub_category and property):
        return Response({'error': 'Hauptkategorie, Unterkategorie und Eigenschaft erforderlich'}, status=400)
    
    components = Component.objects.filter(
        main_category_id=main_category,
        sub_category_id=sub_category
    )
    values = set()
    for component in components:
        if property in component.properties:
            values.add(component.properties[property])
    return Response(sorted(values))
```

### 5. Frontend-Integration
Das Frontend (`catalog.html`) aus der vorherigen Antwort ist bereits für dynamische Daten über API-Aufrufe ausgelegt. Es sind keine Änderungen erforderlich, es sei denn, Sie möchten zusätzliche Komponentendetails anzeigen (z. B. `fragment_id`, `model_uuid`). Stellen Sie sicher, dass `catalog.js` `fragment_id` und `model_uuid` für die Darstellung von IFC-Fragmenten im Viewer verwendet.

**Optionales Frontend-Update** (im `catalog.html`-Skript):
```javascript
async function updateFragments() {
    const mainCategory = mainCategorySelect.value;
    const subCategory = subCategorySelect.value;
    const property = propertiesSelect.value;
    const propertyValue = propertyValuesSelect.value;

    fragmentSelect.innerHTML = '<option value="">Wähle ein Fragment</option>';
    loadingIndicator.style.display = 'block';

    try {
        const query = new URLSearchParams({
            ...(mainCategory && { main_category: mainCategory }),
            ...(subCategory && { sub_category: subCategory }),
            ...(property && { property: property }),
            ...(propertyValue && { value: propertyValue })
        }).toString();
        const response = await fetch(`/api/components?${query}`);
        const fragments = await response.json();
        fragments.forEach(fragment => {
            const option = document.createElement('option');
            option.value = fragment.id;
            option.textContent = `${fragment.name} (Ebene: ${fragment.properties.storey})`;
            fragmentSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Fehler beim Laden der Fragmente:', error);
    } finally {
        loadingIndicator.style.display = 'none';
    }
}
```

### 6. Umgang mit unterschiedlichen Inhalten
Um unterschiedliche Materialien oder Eigenschaften in hochgeladenen IFC-Dateien zu berücksichtigen:
- **Materialien**: Die `upload_ifc`-Ansicht extrahiert Materialien dynamisch aus `HasAssociations` oder parst `Name`/`ObjectType` nach Materialhinweisen (z. B. „Holz“, „Stahl“). Neue Materialien (z. B. „Aluminium“, „Ziegel“) werden automatisch zum `properties.material`-Feld hinzugefügt und erscheinen in der `property_values`-API-Antwort.
- **Abmessungen**: Extrahieren Sie `OverallWidth`, `OverallHeight` oder `thickness`, wo verfügbar, und formatieren Sie sie als Strings (z. B. „1200x2000mm“). Für Elemente ohne Abmessungen verwenden Sie „Unbekannt“ oder holen Sie Geometrie über `ifcopenshell`.
- **Benutzerdefinierte Eigenschaften**: Parsen Sie zusätzliche IFC-Attribute (z. B. `PredefinedType`, `ThermalTransmittance`) und fügen Sie sie bei Relevanz zu `properties` hinzu. Beispiel:
  ```python
  if hasattr(element, 'PredefinedType') and element.PredefinedType:
      properties['vordefinierter_typ'] = element.PredefinedType
  ```
- **Dynamische Unterkategorien**: Wenn ein IFC-Typ nicht in `IFC_TYPE_MAPPING` ist, standardmäßig `sonstige_bauteile` verwenden oder dynamisch eine neue Unterkategorie erstellen:
  ```python
  if ifc_type not in IFC_TYPE_MAPPING:
      sub_cat, _ = SubCategory.objects.get_or_create(
          id=f"custom_{ifc_type.lower()}",
          name=f"{ifc_type.replace('Ifc', '')}",
          main_category=MainCategory.objects.get(id='ausbauelemente'),
          defaults={'ifc_types': [ifc_type]}
      )
      mapping = {'main_category': 'ausbauelemente', 'sub_category': sub_cat.id}
  ```

### 7. Echtzeit-Updates
Die `upload_ifc`-Ansicht löst ein WebSocket-Update aus (falls Django Channels verwendet wird). Stellen Sie sicher, dass das Frontend auf Updates lauscht, wie zuvor gezeigt:
```javascript
const socket = new WebSocket('ws://' + window.location.host + '/ws/components/');
socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.message === 'update') {
        updateFragments();
    }
};
```

### 8. Testen
1. Laden Sie eine IFC-Datei mit anderen Materialien hoch (z. B. „Aluminium“, „Ziegel“).
2. Überprüfen Sie, dass:
   - Neue Komponenten in der richtigen Hauptkategorie und Unterkategorie erscheinen.
   - Das Dropdown `properties` `material`, `abmessungen` usw. mit neuen Werten (z. B. „Aluminium“) enthält.
   - Das Dropdown `property_values` nur in der Datenbank vorhandene Werte anzeigt (z. B. „Aluminium“, „Ziegel“).
   - Die Fragmentliste sich mit neuen Uploads aktualisiert.
3. Testen Sie mit einem unbekannten IFC-Typ (z. B. `IfcPlate`), um sicherzustellen, dass er `sonstige_bauteile` oder einer neuen Unterkategorie zugewiesen wird.

### 9. Zusätzliche Überlegungen
- **Leistung**: Für große IFC-Dateien verwenden Sie Celery für asynchrone Verarbeitung:
  ```python
  from celery import shared_task

  @shared_task
  def process_ifc(file_path):
      ifc = ifcopenshell.open(file_path)
      # Elemente wie oben verarbeiten
      # Komponenten speichern
      # WebSocket-Update auslösen
  ```
- **Validierung**: Validieren Sie IFC-Daten (z. B. nicht-leerer `Name`, gültige Materialien) vor dem Speichern.
- **Erweiterbarkeit**: Erlauben Sie Benutzern, benutzerdefinierte Zuordnungen für neue IFC-Typen über eine Admin-Oberfläche zu definieren.
- **Fehlerbehandlung**: Fügen Sie benutzerorientierte Fehlermeldungen im Frontend für fehlerhafte Uploads oder API-Fehler hinzu.

## Zusammenfassung
Dieses Filtersystem verarbeitet dynamisch unterschiedliche IFC-Inhalte durch:
- Zuordnung von IFC-Typen zu Kategorien mit einer flexiblen `IFC_TYPE_MAPPING`.
- Extrahieren von Eigenschaften (z. B. Materialien, Abmessungen) aus IFC-Feldern.
- Speichern von Komponenten mit dynamischen Eigenschaften in der Datenbank.
- Nutzung bestehender API-Endpunkte zur Bereitstellung von Filteroptionen.
- Unterstützung von Echtzeit-Updates über WebSockets oder Polling.

Das System ist robust genug, um neue Materialien oder Eigenschaften ohne Codeänderungen zu verarbeiten, solange die IFC-Struktur konsistent bleibt. Wenn Sie spezifischen Code für Celery, Admin-Oberflächen oder zusätzliches IFC-Parsing benötigen, lassen Sie es mich wissen!