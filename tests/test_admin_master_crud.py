"""Admin-only Master Data creation and assignment regression cases."""
from __future__ import annotations

from sqlalchemy import func

from app.extensions import db
from app.models import DA, PC, AuditLog, Committee, CommitteeMember, Role, User, Village


def _admin(client, app):
    with app.app_context():
        admin = User(role=Role.ADMIN, display_name='Admin CRUD', email='master-admin@example.org')
        admin.set_password('StrongAdmin123')
        db.session.add(admin)
        db.session.commit()
    assert client.post('/login', data={
        'identifier':'master-admin@example.org','password':'StrongAdmin123'
    }).status_code in (302,303)


def _create(client, key, data):
    return client.post(f'/api/v1/admin/{key}',json=data)


def test_admin_can_create_entire_hierarchy_and_one_linked_login(client, app):
    _admin(client, app)
    pm = _create(client, 'pms', {'full_name':'New PM','email':'pm-contact@example.org'})
    assert pm.status_code == 201, pm.json
    pm_id = pm.json['item']['id']
    pc = _create(client, 'pcs', {
        'full_name':'New PC','cluster':'CSRB','pm_id':pm_id,
        'create_login':True,'login_email':'pc-login@example.org',
        'login_password':'SecretPassword1234'
    })
    assert pc.status_code == 201, pc.json
    assert pc.json['linked_login_created'] is True
    assert pc.json['item']['pm_name'] == 'New PM'
    pc_id = pc.json['item']['id']
    da = _create(client, 'das', {
        'full_name':'New DA','pc_id':pc_id,
        'create_login':True,'login_mobile':'9876543210',
        'login_password':'DifferentPassword1234'
    })
    assert da.status_code == 201, da.json
    assert da.json['linked_login_created'] is True
    da_id = da.json['item']['id']
    village = _create(client, 'villages', {'name':'New Village','da_id':da_id})
    assert village.status_code == 201, village.json
    committee = _create(client, 'committees', {'name':'Water','village_id':village.json['item']['id']})
    assert committee.status_code == 201, committee.json
    member = _create(client,'committee-members',{
        'full_name':'Member One','committee_id':committee.json['item']['id'],
        'gender':'Female','designation':'Member'
    })
    assert member.status_code == 201, member.json
    with app.app_context():
        assert db.session.get(PC,pc_id).pm_id == pm_id
        assert db.session.get(DA,da_id).pc_id == pc_id
        assert db.session.get(Village,village.json['item']['id']).da_id == da_id
        assert db.session.get(Committee,committee.json['item']['id']).village_id == village.json['item']['id']
        assert db.session.get(CommitteeMember,member.json['item']['id']).committee_id == committee.json['item']['id']
        pc_user = db.session.scalar(db.select(User).where(User.pc_id==pc_id))
        da_user = db.session.scalar(db.select(User).where(User.da_id==da_id))
        assert pc_user and pc_user.check_password('SecretPassword1234') and pc_user.role==Role.PC
        assert da_user and da_user.check_password('DifferentPassword1234') and da_user.role==Role.DA
        assert db.session.scalar(db.select(func.count(AuditLog.id))) >= 8
        assert 'SecretPassword1234' not in str(db.session.scalars(db.select(AuditLog)).all())
    client.post('/logout')
    assert client.post('/login', data={
        'identifier':'9876543210','password':'DifferentPassword1234'
    }).status_code in (302,303)


def test_invalid_parent_and_duplicate_login_roll_back_staff_creation(client, app):
    _admin(client, app)
    invalid = _create(client, 'das',{'full_name':'Orphan DA','pc_id':99999})
    assert invalid.status_code == 422
    assert 'Project Coordinators' in invalid.json['error']
    pm = _create(client,'pms',{'full_name':'PM A'})
    pc = _create(client,'pcs',{'full_name':'PC B','cluster':'PDTC','pm_id':pm.json['item']['id']})
    assert pc.status_code == 201
    _create(client,'users',{
        'display_name':'Current DA','role':'admin','email':'taken@example.org',
        'password':'AnotherPassword123'
    })
    failure = _create(client,'das',{
        'full_name':'Not Created','pc_id':pc.json['item']['id'],
        'create_login':True,'login_email':'taken@example.org',
        'login_password':'AnotherPassword123'
    })
    assert failure.status_code == 409, failure.json
    with app.app_context():
        assert db.session.scalar(db.select(func.count(DA.id))) == 0


def test_admin_role_only_and_user_profile_link_validation(client, app):
    assert _create(client,'pms',{'full_name':'Forbidden'}).status_code == 401
    _admin(client, app)
    pm = _create(client,'pms',{'full_name':'PM Login'})
    assert pm.status_code == 201
    result = _create(client,'users',{
        'display_name':'PM account','role':'pm','pm_id':pm.json['item']['id'],
        'email':'new-pm@example.org','password':'AnotherPassword123'
    })
    assert result.status_code == 201, result.json
    missing_link = _create(client,'users',{
        'display_name':'Orphan DA','role':'da','email':'orphan-da@example.org',
        'password':'AnotherPassword123'
    })
    assert missing_link.status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(User).where(User.email=='orphan-da@example.org')) is None


def test_admin_can_provision_existing_staff_and_reset_pm_password(client, app):
    _admin(client, app)
    pm = _create(client,'pms',{'full_name':'Existing PM'})
    assert pm.status_code == 201
    pm_id=pm.json['item']['id']
    result=client.patch(f'/api/v1/admin/pms/{pm_id}',json={
        'create_login':True,'login_email':'existing-pm@example.org',
        'login_password':'StrongPMPassword1234'
    })
    assert result.status_code == 200, result.json
    assert result.json['linked_login_created'] is True
    repeated=client.patch(f'/api/v1/admin/pms/{pm_id}',json={
        'create_login':True,'login_email':'another-pm@example.org',
        'login_password':'StrongPMPassword1234'
    })
    assert repeated.status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(func.count(User.id)).where(User.pm_id==pm_id)) == 1
    reset=client.post(f'/api/v1/admin/pms/{pm_id}/reset-password',json={
        'password':'EvenStrongerPM1234','confirm_password':'EvenStrongerPM1234'
    })
    assert reset.status_code == 200, reset.json
    client.post('/logout')
    assert client.post('/login',data={
        'identifier':'existing-pm@example.org','password':'EvenStrongerPM1234'
    }).status_code in (302,303)
