"""DA-led current-day village attendance and cross-assignment permissions."""
from __future__ import annotations

import io
import json
from datetime import date
from types import SimpleNamespace

from PIL import Image

from app.extensions import db
from app.models import (
    DA, PC, Cluster, Committee, CommitteeMember, Role, User, Village,
    VillageAttendanceVisit,
)
from app.services.monitoring import dashboard_summary, map_markers
from app.services.reports import _village_visit_export_rows, export_report_workbook
from app.timeutils import local_today


def _image():
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _setup(app):
    with app.app_context():
        pc = PC(full_name="PC", cluster=Cluster.CSRB)
        da = DA(full_name="Field DA", pc=pc)
        other_da = DA(full_name="Other DA", pc=pc)
        village = Village(name="Assigned Village", da=da)
        other_village = Village(name="Unassigned Village", da=other_da)
        a = Committee(name="Environment", village=village)
        b = Committee(name="Water", village=village)
        c = Committee(name="Health", village=other_village)
        m1 = CommitteeMember(full_name="Male Member", committee=a, designation="President", gender="Male")
        m2 = CommitteeMember(full_name="Female Member", committee=b, designation="Secretary", gender="Female")
        m3 = CommitteeMember(full_name="Other Member", committee=c, designation="Member", gender="Female")
        user = User(email="da-led@example.org", role=Role.DA, display_name="Field DA", da=da)
        user.set_password("SuperSecret123")
        db.session.add_all([pc, da, other_da, village, other_village, a, b, c, m1, m2, m3, user])
        db.session.commit()
        return {"assigned": village.id, "other": other_village.id,
                "a": a.id, "b": b.id, "c": c.id, "m1": m1.id, "m2": m2.id,
                "m3": m3.id, "user": user.id}


def _post(client, ids, village_id, rows, submission_id, **extra):
    data = {
        "village_id": str(village_id), "client_submission_id": submission_id,
        "latitude": "17.978123", "longitude": "79.588123",
        "new_members_count": "4", "committees": json.dumps(rows),
        "photo": (_image(), "evidence.png"),
        **extra,
    }
    return client.post("/api/v1/attendance/village", data=data, content_type="multipart/form-data")


def test_da_records_all_committees_without_pc_action_plan(client, app):
    ids = _setup(app)
    client.post("/login", data={"identifier": "da-led@example.org", "password": "SuperSecret123"})
    picker = client.get("/api/v1/attendance/villages")
    assert picker.status_code == 200
    assert {row["id"] for row in picker.json["items"]} == {ids["assigned"], ids["other"]}
    details = client.get(f"/api/v1/attendance/villages/{ids['assigned']}/details")
    assert details.status_code == 200
    assert len(details.json["items"]) == 2
    rows = [
        {"committee_id": ids["a"], "visit_member_ids": [ids["m1"]]},
        {"committee_id": ids["b"], "visit_member_ids": [ids["m2"]]},
    ]
    response = _post(client, ids, ids["assigned"], rows, "da-led-visit-1")
    assert response.status_code == 201, response.get_json()
    with app.app_context():
        visit = db.session.get(VillageAttendanceVisit, response.json["id"])
        assert visit.visit_date == local_today()
        assert visit.new_members_count == 4
        assert visit.outside_assignment is False
        assert len(visit.entries) == 2
        assert all(entry.action_plan_id is None and entry.new_members_count == 0 for entry in visit.entries)
        assert sum(entry.total_count for entry in visit.entries) == 2
        user = db.session.get(User, ids["user"])
        summary = dashboard_summary(user)
        assert summary["counts"]["villages_done"] == 1
        assert summary["counts"]["people_attended"] == 2
        assert summary["counts"]["new_members"] == 4
        workbook = export_report_workbook(user, local_today().replace(day=1))
        exported = list(workbook.active.values)
        assert len(exported) == 3  # header + one selected member per committee
        assert {row[7] for row in exported[1:]} == {"Environment", "Water"}
        assert sum(row[12] or 0 for row in exported[1:]) == 2
        assert sum(row[13] or 0 for row in exported[1:]) == 4
        assert {row[14] for row in exported[1:]} == {"Male Member", "Female Member"}
    duplicate = _post(client, ids, ids["assigned"], rows, "da-led-visit-2")
    assert duplicate.status_code == 422


def test_unassigned_requires_explicit_other_and_date_is_not_editable(client, app):
    ids = _setup(app)
    client.post("/login", data={"identifier": "da-led@example.org", "password": "SuperSecret123"})
    rows = [{"committee_id": ids["c"], "visit_member_ids": [ids["m3"]]}]
    denied = _post(client, ids, ids["other"], rows, "cross-1")
    assert denied.status_code == 403
    tampered = _post(client, ids, ids["other"], rows, "cross-2",
                     other_village="1", visit_date="2020-01-01")
    assert tampered.status_code == 422
    allowed = _post(client, ids, ids["other"], rows, "cross-3", other_village="1")
    assert allowed.status_code == 201, allowed.get_json()
    with app.app_context():
        visit = db.session.get(VillageAttendanceVisit, allowed.json["id"])
        assert visit.outside_assignment is True
        assert visit.new_members_count == 4
        summary = dashboard_summary(db.session.get(User, ids["user"]))
        assert summary["counts"]["villages"] == 1  # assigned-village denominator
        assert summary["counts"]["villages_done"] == 0
        assert summary["counts"]["villages_pending"] == 1
        assert summary["counts"]["other_villages_visited"] == 1
        assert summary["counts"]["people_attended"] == 1
        markers = map_markers(db.session.get(User, ids["user"]))
        assert {marker["id"] for marker in markers} == {ids["assigned"], ids["other"]}
        extra = next(marker for marker in markers if marker["id"] == ids["other"])
        assert extra["outside_assignment"] is True
        assert extra["status"] == "Visited"
    assert client.get(f"/reports/village/{allowed.json['id']}").status_code == 200


def test_village_export_preserves_members_without_repeating_totals():
    """One village-level new-member value, accurate committee totals in Excel."""
    def member(name, role):
        return SimpleNamespace(member_name_snapshot=name, designation_snapshot=role,
                               is_enabled=True, is_deleted=False)

    entries = [
        SimpleNamespace(id=11, committee=SimpleNamespace(name="Environment"),
                        action_plan_id=None, is_enabled=True, is_deleted=False,
                        male_count=1, female_count=1, total_count=2,
                        visited_members=[member("A", "President"), member("B", "Secretary")]),
        SimpleNamespace(id=12, committee=SimpleNamespace(name="Water"),
                        action_plan_id=None, is_enabled=True, is_deleted=False,
                        male_count=0, female_count=0, total_count=0, visited_members=[]),
    ]
    village = SimpleNamespace(name="Demo", da=SimpleNamespace(
        pc=SimpleNamespace(cluster=SimpleNamespace(value="CSRB"), full_name="Coordinator")))
    visit = SimpleNamespace(village=village, visit_date=date(2026, 10, 28),
                            entries=entries, new_members_count=3,
                            remarks="One shared remark", latitude=17.98, longitude=79.53)
    rows = _village_visit_export_rows(visit, "DA")
    assert [row[7] for row in rows] == ["Environment", "Environment", "Water"]
    assert [row[14] for row in rows] == ["A", "B", ""]
    assert sum(row[12] or 0 for row in rows) == 2
    assert sum(row[13] or 0 for row in rows) == 3
    assert sum(bool(row[22]) for row in rows) == 1
    assert all(len(row) == 23 for row in rows)
