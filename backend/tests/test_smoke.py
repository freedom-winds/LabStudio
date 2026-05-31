import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import User
from app.seed import seed


def test_health_and_login(tmp_path):
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"
        UPLOAD_ROOT = tmp_path / "uploads"

    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        seed()
        users = User.query.all()
        assert len(users) == 1
        assert users[0].username == "00000000"
        assert users[0].account_type == "admin"
        student = User(
            username="0260001",
            real_name="测试学生",
            gender="男",
            account_type="student",
            status="active",
            is_first_login=False,
        )
        student.set_password("Student123!")
        db.session.add(student)
        db.session.commit()
        student_id = student.id
    client = app.test_client()
    assert client.get("/api/public/health").status_code == 200
    response = client.post("/api/auth/login", json={"username": "00000000", "password": "Admin1234!"})
    assert response.status_code == 200
    token = response.get_json()["data"]["token"]
    dashboard = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dashboard.status_code == 200
    headers = {"Authorization": f"Bearer {token}"}
    year = client.post("/api/years", json={"name": "2026年", "year_number": 2026}, headers=headers)
    assert year.status_code == 201
    year_id = year.get_json()["data"]["id"]
    topic = client.post("/api/topics", json={"year_id": year_id, "title": "材料表征实验"}, headers=headers)
    assert topic.status_code == 201
    topic_id = topic.get_json()["data"]["id"]
    team = client.post("/api/teams", json={"year_id": year_id, "name": "先进材料组"}, headers=headers)
    assert team.status_code == 201
    team_id = team.get_json()["data"]["id"]
    experiment = client.post(
        "/api/experiments",
        json={"team_id": team_id, "topic_id": topic_id, "name": "材料表征实验"},
        headers=headers,
    )
    assert experiment.status_code == 201
    experiments = client.get("/api/experiments", headers=headers)
    assert experiments.status_code == 200
    assert experiments.get_json()["data"]["total"] == 1
    dashboard = client.get("/api/dashboard", headers=headers)
    dashboard_data = dashboard.get_json()["data"]
    assert dashboard_data["overview"]["teams"] == 1
    assert dashboard_data["overview"]["experiments"] == 1
    assert dashboard_data["overview_details"]["teams"]["leaders"] == 1
    reservation = client.post(
        "/api/reservations",
        json={
            "start_time": "2026-05-31T09:00",
            "end_time": "2026-05-31T11:00",
            "purpose": "预约测试",
        },
        headers=headers,
    )
    assert reservation.status_code == 201
    reservation_id = reservation.get_json()["data"]["id"]
    rejected = client.post(
        f"/api/reservations/{reservation_id}/approve",
        json={"status": "rejected"},
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.get_json()["data"]["final_status"] == "rejected"
    chat = client.post("/api/chats", json={"user_id": student_id}, headers=headers)
    assert chat.status_code == 201
    chat_id = chat.get_json()["data"]["id"]
    same_chat = client.post("/api/chats", json={"user_id": student_id}, headers=headers)
    assert same_chat.status_code == 200
    assert same_chat.get_json()["data"]["id"] == chat_id
    deleted = client.delete(f"/api/chats/{chat_id}", headers=headers)
    assert deleted.status_code == 200
