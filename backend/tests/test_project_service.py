from app.models.project import Project


# ─── create_project ───────────────────────────────────────────────────────────

class TestCreateProject:

    def test_create_project_valid_returns_201(self, client, db_session, auth_headers, seeded_pm_user):
        payload = {
            'project_code': 'TSTP',
            'project_name': '单测项目',
            'product_type': 'SUS_VC',
            'project_owner_id': seeded_pm_user.id,
        }
        res = client.post('/api/projects/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 201
        data = res.get_json()['data']
        assert data['project_code'] == 'TSTP'
        assert db_session.get(Project, data['id']) is not None

    def test_create_project_missing_name_returns_400(self, client, auth_headers, seeded_pm_user):
        payload = {
            'project_code': 'NONAM',
            'product_type': 'SUS_VC',
            'project_owner_id': seeded_pm_user.id,
        }
        res = client.post('/api/projects/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_create_project_duplicate_code_returns_409(self, client, auth_headers, seeded_pm_user):
        payload = {
            'project_code': 'DUPX',
            'project_name': '重复编码项目',
            'product_type': 'SUS_VC',
            'project_owner_id': seeded_pm_user.id,
        }
        res1 = client.post('/api/projects/', json=payload, headers=auth_headers['pm'])
        assert res1.status_code == 201
        res2 = client.post('/api/projects/', json=payload, headers=auth_headers['pm'])
        assert res2.status_code == 409
        assert res2.get_json()['code'] == 409

    def test_create_project_unauthorized_role_returns_403(self, client, auth_headers, seeded_pm_user):
        payload = {
            'project_code': 'NOPER',
            'project_name': '无权限项目',
            'product_type': 'SUS_VC',
            'project_owner_id': seeded_pm_user.id,
        }
        res = client.post('/api/projects/', json=payload, headers=auth_headers['iqc'])
        assert res.status_code == 403
        assert res.get_json()['code'] == 403

    def test_create_project_invalid_product_type_returns_400(self, client, auth_headers, seeded_pm_user):
        payload = {
            'project_code': 'INVP',
            'project_name': '非法类型项目',
            'product_type': 'INVALID',
            'project_owner_id': seeded_pm_user.id,
        }
        res = client.post('/api/projects/', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400


# ─── update_project ───────────────────────────────────────────────────────────

class TestUpdateProject:

    def test_update_project_valid_returns_200(self, client, auth_headers, seeded_project):
        project_id = seeded_project.id
        payload = {'project_name': '项目改名', 'version': 0}
        res = client.put(f'/api/projects/{project_id}', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 200
        data = res.get_json()['data']
        assert data['project_name'] == '项目改名'
        assert data['version'] == 1

    def test_update_project_missing_version_returns_400(self, client, auth_headers, seeded_project):
        project_id = seeded_project.id
        payload = {'project_name': '缺版本号'}
        res = client.put(f'/api/projects/{project_id}', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_update_project_stale_version_returns_409(self, client, auth_headers, seeded_project):
        project_id = seeded_project.id
        payload = {'project_name': '过期版本测试', 'version': -1}
        res = client.put(f'/api/projects/{project_id}', json=payload, headers=auth_headers['pm'])
        assert res.status_code == 409
        assert res.get_json()['code'] == 409


# ─── cancel_project ───────────────────────────────────────────────────────────

class TestCancelProject:

    def test_cancel_project_active_returns_200(self, client, auth_headers, seeded_project, seeded_pm_user):
        project_id = seeded_project.id
        pm_id = seeded_pm_user.id
        res = client.patch(
            f'/api/projects/{project_id}/cancel',
            json={'reason': '测试取消原因', 'version': 0},
            headers=auth_headers['pm'],
        )
        assert res.status_code == 200
        data = res.get_json()['data']
        assert data['status'] == 'cancelled'
        assert data['cancelled_at'] is not None
        assert data['cancelled_by'] == pm_id
        assert data['version'] == 1

    def test_cancel_project_already_cancelled_returns_400(self, client, auth_headers, seeded_project):
        project_id = seeded_project.id
        res1 = client.patch(
            f'/api/projects/{project_id}/cancel',
            json={'reason': '首次取消', 'version': 0},
            headers=auth_headers['pm'],
        )
        assert res1.status_code == 200
        new_version = res1.get_json()['data']['version']
        res2 = client.patch(
            f'/api/projects/{project_id}/cancel',
            json={'reason': '二次取消', 'version': new_version},
            headers=auth_headers['pm'],
        )
        assert res2.status_code == 400
        assert res2.get_json()['code'] == 400

    def test_cancel_project_missing_reason_returns_400(self, client, auth_headers, seeded_project):
        project_id = seeded_project.id
        res = client.patch(
            f'/api/projects/{project_id}/cancel',
            json={'version': 0},
            headers=auth_headers['pm'],
        )
        assert res.status_code == 400
        assert res.get_json()['code'] == 400

    def test_cancel_project_missing_version_returns_400(self, client, auth_headers, seeded_project):
        project_id = seeded_project.id
        res = client.patch(
            f'/api/projects/{project_id}/cancel',
            json={'reason': '缺版本字段'},
            headers=auth_headers['pm'],
        )
        assert res.status_code == 400
        assert res.get_json()['code'] == 400


# ─── transfer_project_owner ───────────────────────────────────────────────────

class TestTransferProjectOwner:

    def test_transfer_owner_super_admin_returns_200(
        self, client, auth_headers, seeded_project, seeded_super_admin_user
    ):
        project_id = seeded_project.id
        new_owner_id = seeded_super_admin_user.id
        res = client.put(
            f'/api/projects/{project_id}/owner',
            json={'new_owner_id': new_owner_id, 'version': 0},
            headers=auth_headers['super_admin'],
        )
        assert res.status_code == 200
        data = res.get_json()['data']
        assert data['project_owner_id'] == new_owner_id
        assert data['version'] == 1

    def test_transfer_owner_unauthorized_role_returns_403(
        self, client, auth_headers, seeded_project, seeded_super_admin_user
    ):
        project_id = seeded_project.id
        res = client.put(
            f'/api/projects/{project_id}/owner',
            json={'new_owner_id': seeded_super_admin_user.id, 'version': 0},
            headers=auth_headers['pm'],
        )
        assert res.status_code == 403
        assert res.get_json()['code'] == 403


# ─── list_projects ────────────────────────────────────────────────────────────

class TestListProjects:

    def test_list_projects_default_returns_200(self, client, auth_headers):
        res = client.get('/api/projects/', headers=auth_headers['pm'])
        assert res.status_code == 200
        data = res.get_json()['data']
        assert 'items' in data
        assert 'total' in data
        assert data['page'] == 1
        assert data['per_page'] == 20

    def test_list_projects_filter_product_type(self, client, db_session, auth_headers, seeded_pm_user):
        owner_id = seeded_pm_user.id
        created_by = seeded_pm_user.id
        db_session.add_all([
            Project(project_code='SUSP', project_name='SUS项目', product_type='SUS_VC',
                    project_owner_id=owner_id, status='active', created_by=created_by, version=0),
            Project(project_code='CUPP', project_name='CU项目', product_type='CU_VC',
                    project_owner_id=owner_id, status='active', created_by=created_by, version=0),
        ])
        db_session.flush()
        res = client.get('/api/projects/?product_type=SUS_VC', headers=auth_headers['pm'])
        assert res.status_code == 200
        items = res.get_json()['data']['items']
        assert len(items) >= 1
        assert all(i['product_type'] == 'SUS_VC' for i in items)

    def test_list_projects_filter_status(self, client, db_session, auth_headers, seeded_pm_user):
        owner_id = seeded_pm_user.id
        created_by = seeded_pm_user.id
        db_session.add_all([
            Project(project_code='ACTP', project_name='活动项目', product_type='SUS_VC',
                    project_owner_id=owner_id, status='active', created_by=created_by, version=0),
            Project(project_code='CCLP', project_name='已取消项目', product_type='SUS_VC',
                    project_owner_id=owner_id, status='cancelled', created_by=created_by, version=1),
        ])
        db_session.flush()
        res = client.get('/api/projects/?status=cancelled', headers=auth_headers['pm'])
        assert res.status_code == 200
        items = res.get_json()['data']['items']
        assert len(items) >= 1
        assert all(i['status'] == 'cancelled' for i in items)

    def test_list_projects_keyword_search(self, client, db_session, auth_headers, seeded_pm_user):
        owner_id = seeded_pm_user.id
        created_by = seeded_pm_user.id
        db_session.add(Project(
            project_code='KWDP', project_name='关键词搜索测试', product_type='SUS_VC',
            project_owner_id=owner_id, status='active', created_by=created_by, version=0,
        ))
        db_session.flush()
        res = client.get('/api/projects/?keyword=关键词', headers=auth_headers['pm'])
        assert res.status_code == 200
        items = res.get_json()['data']['items']
        assert any('关键词' in i['project_name'] for i in items)
