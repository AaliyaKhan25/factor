"""Joining by business code: no access until the owner approves."""
from datetime import timedelta

from sqlalchemy import select

from app.models.activity_log import ActivityLog
from app.models.invite_code import InviteCode
from app.utils.time import utcnow
from tests.conftest import member_id, new_owner, register


def join(client, headers, code):
    return client.post("/team/join", json={"code": code}, headers=headers)


def test_code_alone_gives_no_access(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")

    assert join(client, helper, code).status_code == 202
    assert client.get("/business", headers=helper).status_code == 403
    assert client.get("/auth/me", headers=helper).json()["memberships"][0]["status"] == "pending"


def test_code_is_accepted_in_any_case_and_without_the_hyphen(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    assert join(client, helper, code.lower().replace("-", " ")).status_code == 202


def test_owner_approval_grants_employee_access_only(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)

    mid = member_id(client, owner, "helper@example.com")
    r = client.post(f"/team/members/{mid}/approve", json={}, headers=owner)
    assert r.status_code == 200
    assert r.json()["role"] == "employee"

    details = client.get("/business", headers=helper)
    assert details.status_code == 200
    assert "business_code" not in details.json()           # only the owner sees the code
    assert client.get("/team/members", headers=helper).status_code == 403
    assert client.post("/business/code/regenerate", headers=helper).status_code == 403


def test_preset_sets_role_and_permissions(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")

    r = client.post(f"/team/members/{mid}/approve", json={"preset": "manager"}, headers=owner)
    assert r.json()["role"] == "asset_manager"
    assert {"confirm_payments", "approve_cases", "reply_to_chats"} <= set(r.json()["permissions"])
    assert "manage_team" not in r.json()["permissions"]


def test_owner_can_change_access_later(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")
    client.post(f"/team/members/{mid}/approve", json={}, headers=owner)

    r = client.patch(f"/team/members/{mid}", json={"permissions": ["confirm_payments"]}, headers=owner)
    assert r.status_code == 200
    assert "confirm_payments" in client.get("/business", headers=helper).json()["your_permissions"]


def test_the_admin_role_can_never_be_assigned(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")

    assert client.post(f"/team/members/{mid}/approve", json={"role": "admin"}, headers=owner).status_code == 422
    assert client.post(f"/team/members/{mid}/approve", json={"role": "employee", "preset": "helper"}, headers=owner).status_code == 422


def test_admin_only_permissions_cannot_be_granted(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")

    r = client.post(f"/team/members/{mid}/approve", json={"permissions": ["manage_team"]}, headers=owner)
    assert r.status_code == 422


def test_a_team_member_cannot_approve_anyone(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")
    client.post(f"/team/members/{mid}/approve", json={"preset": "manager"}, headers=owner)

    newcomer = register(client, "newcomer@example.com")
    join(client, newcomer, code)
    pending_id = member_id(client, owner, "newcomer@example.com")
    r = client.post(f"/team/members/{pending_id}/approve", json={}, headers=helper)
    assert r.status_code == 403


def test_regenerating_revokes_the_old_code(client):
    owner, old_code = new_owner(client)
    new_code = client.post("/business/code/regenerate", headers=owner).json()["business_code"]
    assert new_code != old_code

    late = register(client, "late@example.com")
    assert join(client, late, old_code).status_code == 400
    assert join(client, late, new_code).status_code == 202


def test_unknown_and_revoked_codes_look_identical(client):
    owner, old_code = new_owner(client)
    client.post("/business/code/regenerate", headers=owner)
    someone = register(client, "someone@example.com")

    revoked = join(client, someone, old_code)
    unknown = join(client, someone, "ZZZZ-ZZZZ")
    assert revoked.status_code == unknown.status_code == 400
    assert revoked.json() == unknown.json()


def test_expired_code_is_rejected(client, session_factory):
    owner, code = new_owner(client)
    with session_factory() as db:
        row = db.scalar(select(InviteCode).where(InviteCode.code == code))
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    helper = register(client, "helper@example.com")
    assert join(client, helper, code).status_code == 400


def test_single_use_code_works_once(client):
    owner, _ = new_owner(client)
    code = client.post("/business/code/regenerate?single_use=true", headers=owner).json()["business_code"]
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    assert join(client, first, code).status_code == 202
    assert join(client, second, code).status_code == 400


def test_rejected_person_can_ask_again_but_starts_as_plain_pending(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")
    assert client.post(f"/team/members/{mid}/reject", headers=owner).status_code == 200
    assert client.get("/business", headers=helper).status_code == 403

    assert join(client, helper, code).status_code == 202
    row = client.get("/team/members", headers=owner).json()[1]
    assert (row["status"], row["role"]) == ("pending", "employee")


def test_removed_member_loses_access_immediately(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")
    client.post(f"/team/members/{mid}/approve", json={}, headers=owner)
    assert client.get("/business", headers=helper).status_code == 200

    assert client.delete(f"/team/members/{mid}", headers=owner).status_code == 200
    assert client.get("/business", headers=helper).status_code == 403


def test_the_owner_cannot_be_removed(client):
    owner, _ = new_owner(client)
    owner_member_id = client.get("/team/members", headers=owner).json()[0]["id"]
    assert client.delete(f"/team/members/{owner_member_id}", headers=owner).status_code == 400


def test_pending_request_cannot_be_approved_twice(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")
    assert client.post(f"/team/members/{mid}/approve", json={}, headers=owner).status_code == 200
    assert client.post(f"/team/members/{mid}/approve", json={}, headers=owner).status_code == 409


def test_someone_in_a_business_cannot_join_another(client):
    owner_a, code_a = new_owner(client, "a@example.com", "Shop A")
    owner_b, code_b = new_owner(client, "b@example.com", "Shop B")
    assert join(client, owner_a, code_b).status_code == 409


def test_join_and_approval_are_logged(client, session_factory):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    join(client, helper, code)
    mid = member_id(client, owner, "helper@example.com")
    client.post(f"/team/members/{mid}/approve", json={}, headers=owner)

    with session_factory() as db:
        actions = set(db.scalars(select(ActivityLog.action)).all())
    assert {"business.create", "team.join_requested", "team.approved"} <= actions
