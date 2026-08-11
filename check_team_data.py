from app.db import SessionLocal
from app.models import Team

db = SessionLocal()
team = db.query(Team).filter(Team.school == "Alabama").first()

if team:
    print(f"School: {team.school}")
    print(f"Conference: {team.conference}")
    print(f"Division: {team.division}")
    print(f"Latitude: {team.latitude}")
    print(f"Longitude: {team.longitude}")
    print(f"Is dome: {team.is_dome}")
else:
    print("Alabama not found - check spelling/data")

db.close()