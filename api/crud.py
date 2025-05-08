from .database import SessionLocal, Project, Component

def create_project(name, location, components):
    db = SessionLocal()
    project = Project(name=name, location=location)
    db.add(project)
    db.commit()
    db.refresh(project)

    for comp in components:
        db.add(Component(name=comp['name'], type=comp['type'], project_id=project.id))

    db.commit()
    db.close()
    return project
