"""
test_iqc_service.py — Phase 3 Step 3-11-1
覆盖：GoodsReceiptService / IqcService / EmergencyAuthService
端点：POST / GET /api/goods-receipts/
      POST / GET /api/iqc-reports/
      POST / GET /api/emergency-auth-records/
      PATCH /api/iqc-reports/:id/approve         (Phase 4 占位 → 501)
      PATCH /api/emergency-auth-records/:id/approve (Phase 4 占位 → 501)
"""
from io import BytesIO
from unittest.mock import patch
from datetime import datetime

from app.models.emergency_auth_record import EmergencyAuthRecord


# ══════════════════════════════════════════════════════════════════════════════
# goods_receipt — 到货签收
# ══════════════════════════════════════════════════════════════════════════════

class TestSignReceive:

    def test_sign_receive_happy_path(
        self, client, auth_headers, seeded_fixture, db_session
    ):
        """到货签收：201 + fixture_id / received_qty 落库"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'actual_arrival_date': '2026-05-17',
            'received_qty': 1,
        }
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['warehouse']
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['fixture_id'] == seeded_fixture.id
        assert data['received_qty'] == 1
        assert data['purchase_order_id'] is None

    def test_sign_receive_with_optional_po(
        self, client, auth_headers, seeded_fixture, seeded_po, db_session
    ):
        """到货签收含 purchase_order_id（可选 FK）：201 + po_id 落库"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'purchase_order_id': seeded_po.id,
            'actual_arrival_date': '2026-05-17',
            'received_qty': 2,
        }
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['warehouse']
        )
        assert resp.status_code == 201
        assert resp.get_json()['data']['purchase_order_id'] == seeded_po.id

    def test_sign_receive_missing_fixture_id_returns_400(
        self, client, auth_headers
    ):
        """缺 fixture_id：400"""
        payload = {'actual_arrival_date': '2026-05-17', 'received_qty': 1}
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['warehouse']
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_sign_receive_qty_zero_returns_400(
        self, client, auth_headers, seeded_fixture
    ):
        """received_qty=0（须≥1）：400"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'actual_arrival_date': '2026-05-17',
            'received_qty': 0,
        }
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['warehouse']
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_sign_receive_nonexistent_fixture_returns_404(
        self, client, auth_headers
    ):
        """治具不存在：404"""
        payload = {
            'fixture_id': 99999,
            'actual_arrival_date': '2026-05-17',
            'received_qty': 1,
        }
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['warehouse']
        )
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404

    def test_sign_receive_forbidden_for_pm(
        self, client, auth_headers, seeded_fixture
    ):
        """pm 无权到货签收：403（warehouse / super_admin 专属）"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'actual_arrival_date': '2026-05-17',
            'received_qty': 1,
        }
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['pm']
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_sign_receive_forbidden_for_iqc(
        self, client, auth_headers, seeded_fixture
    ):
        """iqc 无权到货签收：403"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'actual_arrival_date': '2026-05-17',
            'received_qty': 1,
        }
        resp = client.post(
            '/api/goods-receipts/', json=payload, headers=auth_headers['iqc']
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# iqc_report — IQC 检验报告
# ══════════════════════════════════════════════════════════════════════════════

class TestSubmitIqcReport:

    def _post_iqc_report(self, client, headers, fixture_id, iqc_user_id,
                         result='pass', include_file=False):
        data = {
            'fixture_id': str(fixture_id),
            'result': result,
            'inspection_date': '2026-05-17T10:00:00',
            'inspector_id': str(iqc_user_id),
        }
        if include_file:
            data['file'] = (BytesIO(b'fake report content'), 'report.pdf')
            ctx = patch('app.services.iqc_service.save_upload',
                        return_value='iqc/fake/report.pdf')
        else:
            from contextlib import nullcontext
            ctx = nullcontext()
        with ctx:
            return client.post(
                '/api/iqc-reports/',
                headers=headers,
                data=data,
                content_type='multipart/form-data',
            )

    def test_submit_iqc_report_pass_without_file(
        self, client, auth_headers, seeded_fixture, seeded_iqc_user, db_session
    ):
        """IQC 结果 pass（无文件）：201 + result=pass + file_path=null"""
        resp = self._post_iqc_report(
            client, auth_headers['iqc'], seeded_fixture.id, seeded_iqc_user.id, result='pass'
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['result'] == 'pass'
        assert data['fixture_id'] == seeded_fixture.id
        assert data['file_path'] is None

    def test_submit_iqc_report_pass_with_file(
        self, client, auth_headers, seeded_fixture, seeded_iqc_user, db_session
    ):
        """IQC 结果 pass（含文件上传）：201 + file_path 来自 mock"""
        resp = self._post_iqc_report(
            client, auth_headers['iqc'], seeded_fixture.id, seeded_iqc_user.id,
            result='pass', include_file=True,
        )
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['file_path'] == 'iqc/fake/report.pdf'

    def test_submit_iqc_report_fail(
        self, client, auth_headers, seeded_fixture, seeded_iqc_user, db_session
    ):
        """IQC 结果 fail：201 + 单据落库（Phase 4 三方审批 TODO，本步不触发）"""
        resp = self._post_iqc_report(
            client, auth_headers['iqc'], seeded_fixture.id, seeded_iqc_user.id, result='fail'
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        assert resp.get_json()['data']['result'] == 'fail'

    def test_submit_iqc_report_concession(
        self, client, auth_headers, seeded_fixture, seeded_iqc_user, db_session
    ):
        """IQC 结果 concession：201 + 单据落库（Phase 4 让步审批 TODO，本步不触发）"""
        resp = self._post_iqc_report(
            client, auth_headers['iqc'], seeded_fixture.id, seeded_iqc_user.id,
            result='concession',
        )
        assert resp.status_code == 201
        assert resp.get_json()['data']['result'] == 'concession'

    def test_submit_iqc_report_invalid_result_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_iqc_user
    ):
        """result 枚举非法：400"""
        resp = self._post_iqc_report(
            client, auth_headers['iqc'], seeded_fixture.id, seeded_iqc_user.id,
            result='invalid_result',
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_submit_iqc_report_forbidden_for_pm(
        self, client, auth_headers, seeded_fixture, seeded_pm_user
    ):
        """pm 无权提交 IQC 报告：403（iqc / super_admin 专属）"""
        resp = client.post(
            '/api/iqc-reports/',
            headers=auth_headers['pm'],
            data={
                'fixture_id': str(seeded_fixture.id),
                'result': 'pass',
                'inspection_date': '2026-05-17T10:00:00',
                'inspector_id': str(seeded_pm_user.id),
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_submit_iqc_report_forbidden_for_warehouse(
        self, client, auth_headers, seeded_fixture, seeded_warehouse_user
    ):
        """warehouse 无权提交 IQC 报告：403"""
        resp = client.post(
            '/api/iqc-reports/',
            headers=auth_headers['warehouse'],
            data={
                'fixture_id': str(seeded_fixture.id),
                'result': 'pass',
                'inspection_date': '2026-05-17T10:00:00',
                'inspector_id': str(seeded_warehouse_user.id),
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# emergency_auth — 紧急上机授权
# ══════════════════════════════════════════════════════════════════════════════

class TestEmergencyAuth:

    def _build_payload(self, fixture_id, iqc_report_id, pm_id, iqc_id):
        return {
            'fixture_id': fixture_id,
            'iqc_report_id': iqc_report_id,
            'risk_description': '测试风险说明：需要紧急上机验证',
            'authorized_by_pm': pm_id,
            'authorized_by_iqc': iqc_id,
            'authorization_date': '2026-05-17T10:00:00',
        }

    def test_create_emergency_auth_happy_path(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report,
        seeded_pm_user, seeded_iqc_user, db_session
    ):
        """紧急上机授权：201 + 单据落库（Phase 4 审批 TODO，本步不触发）"""
        payload = self._build_payload(
            seeded_fixture.id, seeded_iqc_report.id,
            seeded_pm_user.id, seeded_iqc_user.id,
        )
        resp = client.post(
            '/api/emergency-auth-records/', json=payload, headers=auth_headers['pm']
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['fixture_id'] == seeded_fixture.id
        assert data['iqc_report_id'] == seeded_iqc_report.id
        assert data['authorized_by_pm'] == seeded_pm_user.id
        assert data['authorized_by_iqc'] == seeded_iqc_user.id
        assert data['risk_description'] == '测试风险说明：需要紧急上机验证'

    def test_create_emergency_auth_missing_risk_description_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report,
        seeded_pm_user, seeded_iqc_user
    ):
        """缺 risk_description：400 ValidationError"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'iqc_report_id': seeded_iqc_report.id,
            'authorized_by_pm': seeded_pm_user.id,
            'authorized_by_iqc': seeded_iqc_user.id,
            'authorization_date': '2026-05-17T10:00:00',
        }
        resp = client.post(
            '/api/emergency-auth-records/', json=payload, headers=auth_headers['pm']
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_create_emergency_auth_empty_risk_description_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report,
        seeded_pm_user, seeded_iqc_user
    ):
        """空白 risk_description（仅空格）：400"""
        payload = self._build_payload(
            seeded_fixture.id, seeded_iqc_report.id,
            seeded_pm_user.id, seeded_iqc_user.id,
        )
        payload['risk_description'] = '   '
        resp = client.post(
            '/api/emergency-auth-records/', json=payload, headers=auth_headers['pm']
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_create_emergency_auth_missing_authorized_by_iqc_returns_400(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report, seeded_pm_user
    ):
        """缺 authorized_by_iqc（双签必填）：400"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'iqc_report_id': seeded_iqc_report.id,
            'risk_description': '测试',
            'authorized_by_pm': seeded_pm_user.id,
            'authorization_date': '2026-05-17T10:00:00',
        }
        resp = client.post(
            '/api/emergency-auth-records/', json=payload, headers=auth_headers['pm']
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_create_emergency_auth_forbidden_for_warehouse(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report,
        seeded_pm_user, seeded_iqc_user
    ):
        """warehouse 无权创建紧急上机授权：403（pm / iqc / super_admin 专属）"""
        payload = self._build_payload(
            seeded_fixture.id, seeded_iqc_report.id,
            seeded_pm_user.id, seeded_iqc_user.id,
        )
        resp = client.post(
            '/api/emergency-auth-records/', json=payload, headers=auth_headers['warehouse']
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_create_emergency_auth_forbidden_for_purchaser(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report,
        seeded_pm_user, seeded_iqc_user
    ):
        """purchaser 无权创建紧急上机授权：403"""
        payload = self._build_payload(
            seeded_fixture.id, seeded_iqc_report.id,
            seeded_pm_user.id, seeded_iqc_user.id,
        )
        resp = client.post(
            '/api/emergency-auth-records/', json=payload, headers=auth_headers['purchaser']
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4 占位端点 — 必须返回 501（确认未提早实现）
# ══════════════════════════════════════════════════════════════════════════════

class TestApprovalStubs:

    def test_iqc_report_approve_stub_returns_501(
        self, client, auth_headers, seeded_iqc_report
    ):
        """IQC 不合格三方审批 Phase 4 占位端点：501"""
        resp = client.patch(
            f'/api/iqc-reports/{seeded_iqc_report.id}/approve',
            json={},
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 501
        assert resp.get_json()['code'] == 501

    def test_emergency_auth_approve_stub_returns_501(
        self, client, auth_headers, seeded_fixture, seeded_iqc_report,
        seeded_pm_user, seeded_iqc_user, db_session
    ):
        """紧急上机审批 Phase 4 占位端点：501"""
        record = EmergencyAuthRecord(
            fixture_id=seeded_fixture.id,
            iqc_report_id=seeded_iqc_report.id,
            risk_description='stub test',
            authorized_by_pm=seeded_pm_user.id,
            authorized_by_iqc=seeded_iqc_user.id,
            authorization_date=datetime(2026, 5, 17, 10, 0, 0),
        )
        db_session.add(record)
        db_session.flush()

        resp = client.patch(
            f'/api/emergency-auth-records/{record.id}/approve',
            json={},
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 501
        assert resp.get_json()['code'] == 501
