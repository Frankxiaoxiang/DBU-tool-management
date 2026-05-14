from app.models.batch import Batch
from app.models.project import Project


# ─── create_batch ─────────────────────────────────────────────────────────────

class TestCreateBatch:

    def test_create_manual_init_batch_returns_201(
        self, client, db_session, auth_headers, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'manual_init',
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        data = res.get_json()['data']
        assert data['batch_type'] == 'manual_init'
        assert data['flow_path'] == 'full'
        assert data['status'] == 'draft'
        assert data['batch_no'].startswith(seeded_project_with_snapshot.project_code)
        assert db_session.get(Batch, data['id']) is not None

    def test_second_manual_init_in_same_project_400(
        self, client, auth_headers, seeded_manual_batch, seeded_project_with_snapshot
    ):
        # seeded_manual_batch 已经是该项目下的 manual_init；再次创建应拒绝
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'manual_init',
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_create_mass_prod_batch_returns_201_with_urgency_flag(
        self, client, auth_headers, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'mass_prod',
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        data = res.get_json()['data']
        assert data['batch_type'] == 'mass_prod'
        assert data['urgency_flag'] is True

    def test_second_mass_prod_in_same_project_400(
        self, client, auth_headers, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'mass_prod',
        }
        res1 = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res1.status_code == 201
        res2 = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res2.status_code == 400
        assert res2.get_json()['code'] == 400

    def test_create_addon_quantity_batch_returns_201(
        self, client, auth_headers, seeded_manual_batch, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'addon_quantity',
            'parent_batch_id': seeded_manual_batch.id,
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        data = res.get_json()['data']
        assert data['batch_type'] == 'addon_quantity'
        assert data['parent_batch_id'] == seeded_manual_batch.id

    def test_create_addon_optimize_batch_returns_201(
        self, client, auth_headers, seeded_manual_batch, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'addon_optimize',
            'parent_batch_id': seeded_manual_batch.id,
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        data = res.get_json()['data']
        assert data['batch_type'] == 'addon_optimize'
        assert data['parent_batch_id'] == seeded_manual_batch.id

    def test_addon_without_parent_batch_400(
        self, client, auth_headers, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'addon_quantity',
            # parent_batch_id 故意缺失
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_addon_parent_in_different_project_400(
        self, client, db_session, auth_headers, seeded_project_with_snapshot, seeded_pm_user
    ):
        # 在另一个项目下直接插入一个批次（不需要快照），再用其 id 作父批次 → 跨项目，应 400
        other_project = Project(
            project_code='OTH1',
            project_name='其他项目',
            product_type='SUS_VC',
            project_owner_id=seeded_pm_user.id,
            status='active',
            created_by=seeded_pm_user.id,
            version=0,
        )
        db_session.add(other_project)
        db_session.flush()
        other_batch = Batch(
            project_id=other_project.id,
            batch_no='OTH1-M0-1',
            batch_type='manual_init',
            flow_path='full',
            status='draft',
            created_by=seeded_pm_user.id,
            version=0,
        )
        db_session.add(other_batch)
        db_session.flush()
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'addon_quantity',
            'parent_batch_id': other_batch.id,
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_simplified_flow_path_override(
        self, client, auth_headers, seeded_project_with_snapshot
    ):
        # manual_init 传 flow_path='simplified'，service 应静默覆盖为 'full'，返回 201 不报错
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'manual_init',
            'flow_path': 'simplified',
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        assert res.get_json()['data']['flow_path'] == 'full'

    def test_create_batch_without_snapshot_400(
        self, client, auth_headers, seeded_project
    ):
        # seeded_project 无任何快照记录，应触发 Rule 6 校验拒绝
        payload = {
            'project_id': seeded_project.id,
            'batch_type': 'manual_init',
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_create_batch_unauthorized_role_returns_403(
        self, client, auth_headers, seeded_project_with_snapshot
    ):
        payload = {
            'project_id': seeded_project_with_snapshot.id,
            'batch_type': 'manual_init',
        }
        res = client.post('/api/batches/', json=payload, headers=auth_headers['iqc'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403


# ─── update_batch ─────────────────────────────────────────────────────────────

class TestUpdateBatch:

    def test_update_batch_valid_returns_200(
        self, client, auth_headers, seeded_manual_batch
    ):
        payload = {'remark': '更新备注', 'version': 0}
        res = client.put(
            f'/api/batches/{seeded_manual_batch.id}',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert res.status_code == 200
        data = res.get_json()['data']
        assert data['remark'] == '更新备注'
        assert data['version'] == 1

    def test_update_batch_missing_version_returns_400(
        self, client, auth_headers, seeded_manual_batch
    ):
        payload = {'remark': '缺 version 字段'}
        res = client.put(
            f'/api/batches/{seeded_manual_batch.id}',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_update_batch_stale_version_returns_409(
        self, client, auth_headers, seeded_manual_batch
    ):
        payload = {'remark': '过期版本测试', 'version': -1}
        res = client.put(
            f'/api/batches/{seeded_manual_batch.id}',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert res.status_code == 409
        assert res.get_json()['code'] == 409


# ─── cancel_batch ─────────────────────────────────────────────────────────────

class TestCancelBatch:

    def test_cancel_draft_batch_returns_200(
        self, client, auth_headers, seeded_manual_batch, seeded_pm_user
    ):
        payload = {'reason': '测试取消原因', 'version': 0}
        res = client.patch(
            f'/api/batches/{seeded_manual_batch.id}/cancel',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert res.status_code == 200
        data = res.get_json()['data']
        assert data['status'] == 'cancelled'
        assert data['cancelled_at'] is not None
        assert data['cancelled_by'] == seeded_pm_user.id
        assert data['version'] == 1


# ─── list_batches ─────────────────────────────────────────────────────────────

class TestListBatches:

    def test_list_batches_under_project(
        self, client, db_session, auth_headers,
        seeded_manual_batch, seeded_project_with_snapshot, seeded_pm_user
    ):
        # 插入另一个项目下的批次，验证 project_id 过滤生效
        other_project = Project(
            project_code='LSTB',
            project_name='过滤测试项目',
            product_type='SUS_VC',
            project_owner_id=seeded_pm_user.id,
            status='active',
            created_by=seeded_pm_user.id,
            version=0,
        )
        db_session.add(other_project)
        db_session.flush()
        other_batch = Batch(
            project_id=other_project.id,
            batch_no='LSTB-M0-1',
            batch_type='manual_init',
            flow_path='full',
            status='draft',
            created_by=seeded_pm_user.id,
            version=0,
        )
        db_session.add(other_batch)
        db_session.flush()

        res = client.get(
            f'/api/batches/?project_id={seeded_project_with_snapshot.id}',
            headers=auth_headers['pm'],
        )
        assert res.status_code == 200
        data = res.get_json()['data']
        items = data['items']
        assert len(items) >= 1
        assert all(i['project_id'] == seeded_project_with_snapshot.id for i in items)
