"""
test_fixture_service.py — Phase 2 Step 2-6-2
覆盖：list_fixtures / create_fixture / update_fixture /
      change_status / force_status / version_bump /
      copy_to_batch / seal_batch
"""
import inspect
import pytest


# ══════════════════════════════════════════════════════════════════════════════
# list_fixtures
# ══════════════════════════════════════════════════════════════════════════════

class TestListFixtures:

    def test_list_fixtures_default_returns_200(self, client, auth_headers, seeded_fixture):
        res = client.get('/api/fixtures/', headers=auth_headers['pm'])
        assert res.status_code == 200
        assert res.get_json()['code'] == 200
        data = res.get_json()['data']
        assert 'items' in data and 'total' in data

    def test_list_fixtures_filter_by_batch_id(self, client, auth_headers, seeded_fixture, seeded_batch):
        res = client.get(f'/api/fixtures/?batch_id={seeded_batch.id}', headers=auth_headers['pm'])
        assert res.status_code == 200
        items = res.get_json()['data']['items']
        assert all(i['batch_id'] == seeded_batch.id for i in items)

    def test_list_fixtures_filter_by_status(self, client, auth_headers, seeded_fixture):
        res = client.get('/api/fixtures/?current_status=pending_iqc', headers=auth_headers['pm'])
        assert res.status_code == 200
        items = res.get_json()['data']['items']
        assert all(i['current_status'] == 'pending_iqc' for i in items)


# ══════════════════════════════════════════════════════════════════════════════
# create_fixture
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateFixture:

    def test_create_fixture_valid_payload_returns_201(
        self, client, auth_headers, seeded_batch, db_session
    ):
        payload = {
            'batch_id': seeded_batch.id,
            'fixture_type_code': 'FB-YN',
        }
        res = client.post('/api/fixtures/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        assert res.get_json()['code'] == 201
        data = res.get_json()['data']
        assert data['fixture_code'] not in (None, '')   # 编码由后端生成（§e.7）
        assert data['set_no'] >= 1

    def test_create_fixture_missing_fixture_type_code_returns_400(
        self, client, auth_headers, seeded_batch
    ):
        payload = {'batch_id': seeded_batch.id}
        res = client.post('/api/fixtures/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_create_fixture_missing_batch_id_returns_400(self, client, auth_headers):
        payload = {'fixture_type_code': 'FB-YN'}
        res = client.post('/api/fixtures/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_create_fixture_unauthorized_role_returns_403(
        self, client, auth_headers, seeded_batch
    ):
        payload = {'batch_id': seeded_batch.id, 'fixture_type_code': 'FB-YN'}
        res = client.post('/api/fixtures/', json=payload, headers=auth_headers['iqc'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# update_fixture
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateFixture:

    def test_update_fixture_valid_returns_200(
        self, client, auth_headers, seeded_fixture
    ):
        original_version = seeded_fixture.version  # commit 后 identity map expire，需提前保存
        payload = {'lead_time_days': 30, 'version': original_version}
        res = client.put(f'/api/fixtures/{seeded_fixture.id}', json=payload,
                         headers=auth_headers['pm'])
        assert res.status_code == 200
        assert res.get_json()['code'] == 200
        assert res.get_json()['data']['version'] == original_version + 1

    def test_update_fixture_missing_version_returns_400(
        self, client, auth_headers, seeded_fixture
    ):
        res = client.put(f'/api/fixtures/{seeded_fixture.id}',
                         json={'lead_time_days': 10}, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_update_fixture_stale_version_returns_409(
        self, client, auth_headers, seeded_fixture
    ):
        payload = {'lead_time_days': 10, 'version': seeded_fixture.version - 1}
        res = client.put(f'/api/fixtures/{seeded_fixture.id}', json=payload,
                         headers=auth_headers['pm'])
        assert res.status_code == 409
        assert res.get_json()['code'] == 409


# ══════════════════════════════════════════════════════════════════════════════
# change_status（PATCH /api/fixtures/:id/status）
# ══════════════════════════════════════════════════════════════════════════════

class TestChangeStatus:

    def test_change_status_legal_trigger_returns_200_and_writes_history(
        self, client, auth_headers, seeded_fixture, db_session
    ):
        from app.models.fixture_status_history import FixtureStatusHistory
        before_count = db_session.query(FixtureStatusHistory).filter_by(
            fixture_id=seeded_fixture.id
        ).count()

        # pending_iqc → iqc_inspecting via trigger='normal'；normal 只允许 super_admin/me
        payload = {'trigger': 'normal'}
        res = client.patch(f'/api/fixtures/{seeded_fixture.id}/status',
                           json=payload, headers=auth_headers['super_admin'])
        assert res.status_code == 200
        assert res.get_json()['code'] == 200
        assert res.get_json()['data']['current_status'] == 'iqc_inspecting'

        after_count = db_session.query(FixtureStatusHistory).filter_by(
            fixture_id=seeded_fixture.id
        ).count()
        assert after_count == before_count + 1

    def test_change_status_illegal_trigger_returns_error(
        self, client, auth_headers, seeded_fixture
    ):
        payload = {'trigger': 'invalid_trigger_xyz'}
        res = client.patch(f'/api/fixtures/{seeded_fixture.id}/status',
                           json=payload, headers=auth_headers['iqc'])
        assert res.status_code in (400, 422)
        assert res.get_json()['code'] in (400, 422)

    def test_change_status_missing_trigger_returns_400(
        self, client, auth_headers, seeded_fixture
    ):
        res = client.patch(f'/api/fixtures/{seeded_fixture.id}/status',
                           json={}, headers=auth_headers['iqc'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400


# ══════════════════════════════════════════════════════════════════════════════
# force_status（POST /api/fixtures/:id/force-status）
# ══════════════════════════════════════════════════════════════════════════════

class TestForceStatus:

    def test_force_status_super_admin_returns_200_and_writes_audit_log(
        self, client, auth_headers, seeded_fixture, db_session
    ):
        from app.models.audit_log import AuditLog
        before_count = db_session.query(AuditLog).count()

        payload = {'to_status': 'in_stock', 'reason': '超管测试强制跳转'}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/force-status',
                          json=payload, headers=auth_headers['super_admin'])
        assert res.status_code == 200
        assert res.get_json()['code'] == 200

        after_count = db_session.query(AuditLog).count()
        assert after_count == before_count + 1

    def test_force_status_non_super_admin_returns_403(
        self, client, auth_headers, seeded_fixture
    ):
        payload = {'to_status': 'in_stock', 'reason': '非超管强制跳转'}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/force-status',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403

    def test_force_status_empty_reason_returns_error(
        self, client, auth_headers, seeded_fixture
    ):
        payload = {'to_status': 'in_stock', 'reason': ''}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/force-status',
                          json=payload, headers=auth_headers['super_admin'])
        assert res.status_code in (400, 422)
        assert res.get_json()['code'] in (400, 422)


# ══════════════════════════════════════════════════════════════════════════════
# version_bump（POST /api/fixtures/:id/version-bump）
# ══════════════════════════════════════════════════════════════════════════════

class TestVersionBump:

    def test_version_bump_a1_to_a2_returns_200_and_writes_history(
        self, client, auth_headers, seeded_fixture, db_session
    ):
        from app.models.fixture_status_history import FixtureStatusHistory
        before_count = db_session.query(FixtureStatusHistory).filter_by(
            fixture_id=seeded_fixture.id,
            trigger_type='version_bump',
        ).count()

        original_version = seeded_fixture.version  # commit 后 identity map expire，需提前保存
        payload = {'version': original_version}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/version-bump',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 200
        assert res.get_json()['code'] == 200
        data = res.get_json()['data']
        assert data['current_version_code'] == 'A2'
        assert data['version'] == original_version + 1

        after_count = db_session.query(FixtureStatusHistory).filter_by(
            fixture_id=seeded_fixture.id,
            trigger_type='version_bump',
        ).count()
        assert after_count == before_count + 1

        # auxiliary event：from_status == to_status（工艺状态不变，§e.7）
        latest = db_session.query(FixtureStatusHistory).filter_by(
            fixture_id=seeded_fixture.id,
            trigger_type='version_bump',
        ).order_by(FixtureStatusHistory.id.desc()).first()
        assert latest.from_status == latest.to_status

    def test_version_bump_a3_to_b1(
        self, client, auth_headers, seeded_fixture_a3
    ):
        payload = {'version': seeded_fixture_a3.version}
        res = client.post(f'/api/fixtures/{seeded_fixture_a3.id}/version-bump',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 200
        assert res.get_json()['data']['current_version_code'] == 'B1'

    def test_version_bump_stale_version_returns_409(
        self, client, auth_headers, seeded_fixture
    ):
        payload = {'version': seeded_fixture.version - 1}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/version-bump',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 409
        assert res.get_json()['code'] == 409

    def test_version_bump_unauthorized_role_returns_403(
        self, client, auth_headers, seeded_fixture
    ):
        payload = {'version': seeded_fixture.version}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/version-bump',
                          json=payload, headers=auth_headers['warehouse'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# copy_to_batch（POST /api/fixtures/:id/copy-to-batch）
# ══════════════════════════════════════════════════════════════════════════════

class TestCopyToBatch:

    def test_copy_to_batch_valid_returns_201_with_correct_fields(
        self, client, auth_headers, seeded_fixture, seeded_target_batch, db_session
    ):
        payload = {'target_batch_id': seeded_target_batch.id}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/copy-to-batch',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        assert res.get_json()['code'] == 201
        data = res.get_json()['data']
        assert data['parent_fixture_id'] == seeded_fixture.id          # 溯源（§e.7）
        assert data['current_version_code'] == seeded_fixture.current_version_code  # 继承
        assert data['current_status'] == 'pending_iqc'                 # 重走 IQC
        assert data['set_no'] >= 1
        assert data['fixture_code'] not in (None, '')                   # 后端生成（§e.7）

    def test_copy_to_batch_cross_project_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_cross_project_batch
    ):
        payload = {'target_batch_id': seeded_cross_project_batch.id}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/copy-to-batch',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_copy_to_batch_cancelled_target_batch_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_target_batch, db_session
    ):
        seeded_target_batch.status = 'cancelled'
        db_session.flush()

        payload = {'target_batch_id': seeded_target_batch.id}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/copy-to-batch',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_copy_to_batch_cancelled_source_fixture_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_target_batch, db_session
    ):
        seeded_fixture.status = 'cancelled'
        db_session.flush()

        payload = {'target_batch_id': seeded_target_batch.id}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/copy-to-batch',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_copy_to_batch_unauthorized_role_returns_403(
        self, client, auth_headers, seeded_fixture, seeded_target_batch
    ):
        payload = {'target_batch_id': seeded_target_batch.id}
        res = client.post(f'/api/fixtures/{seeded_fixture.id}/copy-to-batch',
                          json=payload, headers=auth_headers['iqc'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# seal_batch（POST /api/fixtures/batch-seal，Step 2-7-1）
# ══════════════════════════════════════════════════════════════════════════════

class TestSealBatch:

    def test_seal_batch_valid_seals_all_fixtures_and_writes_history(
        self, client, auth_headers, seeded_batch, seeded_fixture,
        seeded_mass_prod_batch, db_session
    ):
        from app.models.fixture_status_history import FixtureStatusHistory
        from app.models.fixture import Fixture
        from app.models.batch import Batch

        before_count = db_session.query(FixtureStatusHistory).filter_by(
            trigger_type='batch_seal',
        ).count()
        original_batch_version = seeded_batch.version  # 保存原始值（expire_all 后不可用）

        payload = {'batch_id': seeded_batch.id, 'version': seeded_batch.version}
        res = client.post('/api/fixtures/batch-seal',
                          json=payload, headers=auth_headers['warehouse'])
        assert res.status_code == 200
        assert res.get_json()['code'] == 200

        db_session.expire_all()

        fixtures_in_batch = db_session.query(Fixture).filter_by(
            batch_id=seeded_batch.id
        ).all()
        assert all(f.is_sealed for f in fixtures_in_batch)

        after_count = db_session.query(FixtureStatusHistory).filter_by(
            trigger_type='batch_seal',
        ).count()
        assert after_count == before_count + len(fixtures_in_batch)

        updated_batch = db_session.get(Batch, seeded_batch.id)
        assert updated_batch.version == original_batch_version + 1

    def test_seal_batch_non_manual_init_returns_400(
        self, client, auth_headers, seeded_mass_prod_batch
    ):
        payload = {'batch_id': seeded_mass_prod_batch.id,
                   'version': seeded_mass_prod_batch.version}
        res = client.post('/api/fixtures/batch-seal',
                          json=payload, headers=auth_headers['warehouse'])
        assert res.status_code in (400, 422)
        assert res.get_json()['code'] in (400, 422)

    def test_seal_batch_no_mass_prod_precondition_returns_error(
        self, client, auth_headers, seeded_batch, db_session
    ):
        """同项目无 in_progress/completed mass_prod 批次，不可封存。"""
        payload = {'batch_id': seeded_batch.id, 'version': seeded_batch.version}
        res = client.post('/api/fixtures/batch-seal',
                          json=payload, headers=auth_headers['warehouse'])
        assert res.status_code in (400, 422)
        assert res.get_json()['code'] in (400, 422)

    def test_seal_batch_unauthorized_role_returns_403(
        self, client, auth_headers, seeded_batch
    ):
        payload = {'batch_id': seeded_batch.id, 'version': seeded_batch.version}
        res = client.post('/api/fixtures/batch-seal',
                          json=payload, headers=auth_headers['pm'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403

    def test_seal_batch_stale_version_returns_409(
        self, client, auth_headers, seeded_batch, seeded_mass_prod_batch
    ):
        payload = {'batch_id': seeded_batch.id,
                   'version': seeded_batch.version - 1}
        res = client.post('/api/fixtures/batch-seal',
                          json=payload, headers=auth_headers['warehouse'])
        assert res.status_code == 409
        assert res.get_json()['code'] == 409


# ══════════════════════════════════════════════════════════════════════════════
# 状态机后门防护（必测，CLAUDE.md §e.4）
# ══════════════════════════════════════════════════════════════════════════════

def test_no_back_door_in_transition():
    """
    transition() 函数签名不得含 force / bypass 参数（防止 V1.2 后门重现，CLAUDE.md §e.4）
    """
    from app.services.state_machine import transition
    sig = inspect.signature(transition)
    assert 'force' not in sig.parameters, \
        "transition() 不得含 force 参数（CLAUDE.md §e.4 铁律）"
    assert 'bypass' not in sig.parameters, \
        "transition() 不得含 bypass 参数（CLAUDE.md §e.4 铁律）"
