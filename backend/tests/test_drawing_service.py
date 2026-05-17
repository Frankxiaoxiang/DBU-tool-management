"""
test_drawing_service.py — Phase 3 Step 3-11-1
覆盖：DrawingService.create_drawing / list_drawings / confirm_drawing
端点：POST / GET /api/drawings/ + PATCH /api/drawings/:id/confirm
"""
from io import BytesIO
from unittest.mock import patch


# ══════════════════════════════════════════════════════════════════════════════
# create_drawing
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateDrawing:

    def _upload(self, client, headers, fixture_id, extra_data=None):
        """辅助：multipart 上传，save_upload 已 patch 为返回假路径。"""
        data = {
            'fixture_id': str(fixture_id),
            'version_code': 'A1',
            'drawing_type': 'design_drawing',
            'file': (BytesIO(b'fake pdf content'), 'test.pdf'),
        }
        if extra_data:
            data.update(extra_data)
        with patch('app.services.drawing_service.save_upload',
                   return_value='drawings/fake/test.pdf'):
            return client.post(
                '/api/drawings/',
                headers=headers,
                data=data,
                content_type='multipart/form-data',
            )

    def test_upload_drawing_happy_path(self, client, auth_headers, seeded_fixture, db_session):
        """合法上传：201 + db 记录生成，file_path 来自 mock，confirmed_by=None"""
        resp = self._upload(client, auth_headers['design_engineer'], seeded_fixture.id)
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['fixture_id'] == seeded_fixture.id
        assert data['drawing_type'] == 'design_drawing'
        assert data['file_path'] == 'drawings/fake/test.pdf'
        assert data['is_copied'] is False
        assert data['confirmed_by'] is None

    def test_upload_drawing_is_copied(
        self, client, auth_headers, seeded_fixture, seeded_drawing, db_session
    ):
        """is_copied=True + source_drawing_id：201 + 复制标记落库"""
        resp = self._upload(
            client, auth_headers['design_engineer'], seeded_fixture.id,
            extra_data={
                'is_copied': 'true',
                'source_drawing_id': str(seeded_drawing.id),
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['is_copied'] is True
        assert data['source_drawing_id'] == seeded_drawing.id

    def test_upload_drawing_dfm_type(self, client, auth_headers, seeded_fixture, db_session):
        """dfm_report 类型：201 + drawing_type 正确"""
        data = {
            'fixture_id': str(seeded_fixture.id),
            'version_code': 'A1',
            'drawing_type': 'dfm_report',
            'file': (BytesIO(b'dfm content'), 'report.pdf'),
        }
        with patch('app.services.drawing_service.save_upload',
                   return_value='drawings/fake/dfm.pdf'):
            resp = client.post(
                '/api/drawings/',
                headers=auth_headers['design_engineer'],
                data=data,
                content_type='multipart/form-data',
            )
        assert resp.status_code == 201
        assert resp.get_json()['data']['drawing_type'] == 'dfm_report'

    def test_upload_drawing_missing_file_returns_400(
        self, client, auth_headers, seeded_fixture
    ):
        """缺 file 字段：400 ValidationError"""
        resp = client.post(
            '/api/drawings/',
            headers=auth_headers['design_engineer'],
            data={
                'fixture_id': str(seeded_fixture.id),
                'version_code': 'A1',
                'drawing_type': 'design_drawing',
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_upload_drawing_invalid_drawing_type_returns_400(
        self, client, auth_headers, seeded_fixture
    ):
        """drawing_type 非法枚举：400"""
        with patch('app.services.drawing_service.save_upload',
                   return_value='drawings/fake/test.pdf'):
            resp = client.post(
                '/api/drawings/',
                headers=auth_headers['design_engineer'],
                data={
                    'fixture_id': str(seeded_fixture.id),
                    'version_code': 'A1',
                    'drawing_type': 'invalid_type',
                    'file': (BytesIO(b'fake'), 'test.pdf'),
                },
                content_type='multipart/form-data',
            )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_upload_drawing_nonexistent_fixture_returns_404(
        self, client, auth_headers
    ):
        """治具 ID 不存在：404"""
        with patch('app.services.drawing_service.save_upload',
                   return_value='drawings/fake/test.pdf'):
            resp = client.post(
                '/api/drawings/',
                headers=auth_headers['design_engineer'],
                data={
                    'fixture_id': '99999',
                    'version_code': 'A1',
                    'drawing_type': 'design_drawing',
                    'file': (BytesIO(b'fake'), 'test.pdf'),
                },
                content_type='multipart/form-data',
            )
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404

    def test_upload_drawing_forbidden_for_warehouse(
        self, client, auth_headers, seeded_fixture
    ):
        """warehouse 无权上传图纸：403"""
        resp = client.post(
            '/api/drawings/',
            headers=auth_headers['warehouse'],
            data={
                'fixture_id': str(seeded_fixture.id),
                'version_code': 'A1',
                'drawing_type': 'design_drawing',
                'file': (b'fake', 'test.pdf'),
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_upload_drawing_forbidden_for_iqc(
        self, client, auth_headers, seeded_fixture
    ):
        """iqc 无权上传图纸：403"""
        resp = client.post(
            '/api/drawings/',
            headers=auth_headers['iqc'],
            data={
                'fixture_id': str(seeded_fixture.id),
                'version_code': 'A1',
                'drawing_type': 'design_drawing',
                'file': (b'fake', 'test.pdf'),
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# list_drawings
# ══════════════════════════════════════════════════════════════════════════════

class TestListDrawings:

    def test_list_drawings_returns_200(
        self, client, auth_headers, seeded_drawing, seeded_fixture
    ):
        """PM 查询列表：200 + 返回列表，包含种子图纸"""
        resp = client.get(
            f'/api/drawings/?fixture_id={seeded_fixture.id}',
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 200
        assert resp.get_json()['code'] == 200
        data = resp.get_json()['data']
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]['fixture_id'] == seeded_fixture.id

    def test_list_drawings_missing_fixture_id_returns_400(self, client, auth_headers):
        """缺 fixture_id 参数：400"""
        resp = client.get('/api/drawings/', headers=auth_headers['pm'])
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_list_drawings_nonexistent_fixture_returns_404(self, client, auth_headers):
        """治具 ID 不存在：404"""
        resp = client.get('/api/drawings/?fixture_id=99999', headers=auth_headers['pm'])
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404


# ══════════════════════════════════════════════════════════════════════════════
# confirm_drawing
# ══════════════════════════════════════════════════════════════════════════════

class TestConfirmDrawing:

    def test_pm_confirm_drawing(self, client, auth_headers, seeded_drawing, seeded_pm_user):
        """PM 确认：200 + confirmed_by/confirmed_at 更新，其他字段不变"""
        resp = client.patch(
            f'/api/drawings/{seeded_drawing.id}/confirm',
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 200
        assert resp.get_json()['code'] == 200
        data = resp.get_json()['data']
        assert data['confirmed_by'] == seeded_pm_user.id
        assert data['confirmed_at'] is not None

    def test_confirm_drawing_already_confirmed_returns_409(
        self, client, auth_headers, seeded_drawing
    ):
        """重复确认：409 ConflictError"""
        client.patch(
            f'/api/drawings/{seeded_drawing.id}/confirm',
            headers=auth_headers['pm'],
        )
        resp = client.patch(
            f'/api/drawings/{seeded_drawing.id}/confirm',
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 409

    def test_confirm_drawing_nonexistent_returns_404(self, client, auth_headers):
        """图纸不存在：404"""
        resp = client.patch(
            '/api/drawings/99999/confirm',
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404

    def test_confirm_drawing_forbidden_for_iqc(
        self, client, auth_headers, seeded_drawing
    ):
        """iqc 无权确认图纸：403"""
        resp = client.patch(
            f'/api/drawings/{seeded_drawing.id}/confirm',
            headers=auth_headers['iqc'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_confirm_drawing_forbidden_for_design_engineer(
        self, client, auth_headers, seeded_drawing
    ):
        """design_engineer 无权确认图纸：403"""
        resp = client.patch(
            f'/api/drawings/{seeded_drawing.id}/confirm',
            headers=auth_headers['design_engineer'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403
