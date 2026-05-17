"""
test_purchase_order_service.py — Phase 3 Step 3-11-1
覆盖：PurchaseOrderService.create / add_item / list / get / update / cancel
端点：POST / GET /api/purchase-orders/ + POST /:id/items + PUT /:id + PATCH /:id/cancel
"""


# ══════════════════════════════════════════════════════════════════════════════
# create_purchase_order
# ══════════════════════════════════════════════════════════════════════════════

class TestCreatePurchaseOrder:

    def test_create_po_happy_path(self, client, auth_headers, seeded_supplier, db_session):
        """合法创建 PO 头：201 + po_no 自动生成 + status=open + version=0"""
        payload = {
            'supplier_id': seeded_supplier.id,
            'order_date': '2026-05-17',
        }
        resp = client.post(
            '/api/purchase-orders/', json=payload, headers=auth_headers['purchaser']
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['po_no'].startswith('PO-')
        assert data['status'] == 'open'
        assert data['version'] == 0
        assert data['supplier_id'] == seeded_supplier.id

    def test_create_po_with_optional_fields(
        self, client, auth_headers, seeded_supplier, db_session
    ):
        """带可选字段（contract_no / remark）：201 + 字段落库"""
        payload = {
            'supplier_id': seeded_supplier.id,
            'order_date': '2026-05-17',
            'contract_no': 'CTR-2026-001',
            'total_lead_time_days': 30,
            'remark': '测试备注',
        }
        resp = client.post(
            '/api/purchase-orders/', json=payload, headers=auth_headers['purchaser']
        )
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['contract_no'] == 'CTR-2026-001'
        assert data['remark'] == '测试备注'

    def test_create_po_missing_supplier_returns_400(self, client, auth_headers):
        """缺 supplier_id：400 ValidationError"""
        payload = {'order_date': '2026-05-17'}
        resp = client.post(
            '/api/purchase-orders/', json=payload, headers=auth_headers['purchaser']
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_create_po_nonexistent_supplier_returns_404(self, client, auth_headers):
        """supplier_id 不存在：404 NotFoundError"""
        payload = {'supplier_id': 99999, 'order_date': '2026-05-17'}
        resp = client.post(
            '/api/purchase-orders/', json=payload, headers=auth_headers['purchaser']
        )
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404

    def test_create_po_forbidden_for_pm(self, client, auth_headers, seeded_supplier):
        """pm 无权创建 PO：403"""
        payload = {'supplier_id': seeded_supplier.id, 'order_date': '2026-05-17'}
        resp = client.post(
            '/api/purchase-orders/', json=payload, headers=auth_headers['pm']
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_create_po_forbidden_for_iqc(self, client, auth_headers, seeded_supplier):
        """iqc 无权创建 PO：403"""
        payload = {'supplier_id': seeded_supplier.id, 'order_date': '2026-05-17'}
        resp = client.post(
            '/api/purchase-orders/', json=payload, headers=auth_headers['iqc']
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# add_item
# ══════════════════════════════════════════════════════════════════════════════

class TestAddItem:

    def test_add_item_happy_path(
        self, client, auth_headers, seeded_po, seeded_fixture, db_session
    ):
        """PO 下添加明细项：201 + fixture_id + purchase_order_id 落库"""
        payload = {
            'fixture_id': seeded_fixture.id,
            'unit_price': '1500.00',
            'item_lead_time_days': 30,
        }
        resp = client.post(
            f'/api/purchase-orders/{seeded_po.id}/items',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 201
        assert resp.get_json()['code'] == 201
        data = resp.get_json()['data']
        assert data['fixture_id'] == seeded_fixture.id
        assert data['purchase_order_id'] == seeded_po.id

    def test_add_item_to_nonexistent_po_returns_404(
        self, client, auth_headers, seeded_fixture
    ):
        """PO 不存在：404"""
        payload = {'fixture_id': seeded_fixture.id}
        resp = client.post(
            '/api/purchase-orders/99999/items',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404

    def test_add_item_missing_fixture_id_returns_400(
        self, client, auth_headers, seeded_po
    ):
        """缺 fixture_id：400 ValidationError"""
        resp = client.post(
            f'/api/purchase-orders/{seeded_po.id}/items',
            json={},
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_add_item_forbidden_for_pm(
        self, client, auth_headers, seeded_po, seeded_fixture
    ):
        """pm 无权添加明细项：403"""
        payload = {'fixture_id': seeded_fixture.id}
        resp = client.post(
            f'/api/purchase-orders/{seeded_po.id}/items',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# update_purchase_order
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdatePurchaseOrder:

    def test_update_po_valid_version(self, client, auth_headers, seeded_po):
        """合法更新（正确 version）：200 + version 递增 + 字段更新"""
        original_version = seeded_po.version  # 0（在请求前捕获，避免 savepoint 释放后 ORM 过期重读）
        payload = {
            'version': original_version,
            'remark': '更新后备注',
        }
        resp = client.put(
            f'/api/purchase-orders/{seeded_po.id}',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 200
        assert resp.get_json()['code'] == 200
        data = resp.get_json()['data']
        assert data['version'] == original_version + 1
        assert data['remark'] == '更新后备注'

    def test_update_po_remark_null_update(self, client, auth_headers, seeded_po):
        """remark 更新为 None（'key' in body 模式，§d Rule 5）：200"""
        payload = {
            'version': seeded_po.version,
            'remark': None,
        }
        resp = client.put(
            f'/api/purchase-orders/{seeded_po.id}',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 200
        assert resp.get_json()['data']['remark'] is None

    def test_update_po_missing_version_returns_400(self, client, auth_headers, seeded_po):
        """缺 version 字段：400 ValidationError（§e.5 守卫）"""
        payload = {'remark': '没有版本号'}
        resp = client.put(
            f'/api/purchase-orders/{seeded_po.id}',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_update_po_stale_version_returns_409(self, client, auth_headers, seeded_po):
        """过期 version：409 ConflictError（乐观锁）"""
        payload = {
            'version': seeded_po.version + 999,
            'remark': '冲突测试',
        }
        resp = client.put(
            f'/api/purchase-orders/{seeded_po.id}',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 409

    def test_update_po_forbidden_for_pm(self, client, auth_headers, seeded_po):
        """pm 无权更新 PO：403"""
        payload = {'version': 0, 'remark': '403 测试'}
        resp = client.put(
            f'/api/purchase-orders/{seeded_po.id}',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_update_po_forbidden_for_warehouse(self, client, auth_headers, seeded_po):
        """warehouse 无权更新 PO：403"""
        payload = {'version': 0}
        resp = client.put(
            f'/api/purchase-orders/{seeded_po.id}',
            json=payload,
            headers=auth_headers['warehouse'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# cancel_purchase_order
# ══════════════════════════════════════════════════════════════════════════════

class TestCancelPurchaseOrder:

    def test_cancel_po_happy_path(self, client, auth_headers, seeded_po):
        """合法作废：200 + status=cancelled + cancel_reason 落库"""
        payload = {
            'version': seeded_po.version,
            'cancel_reason': '测试作废原因',
        }
        resp = client.patch(
            f'/api/purchase-orders/{seeded_po.id}/cancel',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 200
        assert resp.get_json()['code'] == 200
        data = resp.get_json()['data']
        assert data['status'] == 'cancelled'
        assert data['cancel_reason'] == '测试作废原因'
        assert data['cancelled_at'] is not None

    def test_cancel_po_missing_cancel_reason_returns_400(
        self, client, auth_headers, seeded_po
    ):
        """缺 cancel_reason：400 ValidationError"""
        payload = {'version': seeded_po.version}
        resp = client.patch(
            f'/api/purchase-orders/{seeded_po.id}/cancel',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_cancel_already_cancelled_po_returns_409(
        self, client, auth_headers, seeded_po
    ):
        """重复作废：409 ConflictError（幂等保护）"""
        payload = {'version': seeded_po.version, 'cancel_reason': '首次作废'}
        client.patch(
            f'/api/purchase-orders/{seeded_po.id}/cancel',
            json=payload,
            headers=auth_headers['purchaser'],
        )
        resp = client.patch(
            f'/api/purchase-orders/{seeded_po.id}/cancel',
            json={'version': seeded_po.version + 1, 'cancel_reason': '重复作废'},
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 409

    def test_cancel_po_forbidden_for_iqc(self, client, auth_headers, seeded_po):
        """iqc 无权作废 PO：403"""
        payload = {'version': 0, 'cancel_reason': '403 测试'}
        resp = client.patch(
            f'/api/purchase-orders/{seeded_po.id}/cancel',
            json=payload,
            headers=auth_headers['iqc'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_cancel_po_forbidden_for_pm(self, client, auth_headers, seeded_po):
        """pm 无权作废 PO：403"""
        payload = {'version': 0, 'cancel_reason': '403 测试'}
        resp = client.patch(
            f'/api/purchase-orders/{seeded_po.id}/cancel',
            json=payload,
            headers=auth_headers['pm'],
        )
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403


# ══════════════════════════════════════════════════════════════════════════════
# list / get purchase_order
# ══════════════════════════════════════════════════════════════════════════════

class TestListGetPurchaseOrder:

    def test_list_purchase_orders_returns_200(
        self, client, auth_headers, seeded_po
    ):
        """PO 列表：200 + data.items 为列表"""
        resp = client.get('/api/purchase-orders/', headers=auth_headers['purchaser'])
        assert resp.status_code == 200
        assert resp.get_json()['code'] == 200
        data = resp.get_json()['data']
        assert 'items' in data and 'total' in data

    def test_get_purchase_order_returns_200(self, client, auth_headers, seeded_po):
        """PO 详情：200 + 含 items 列表"""
        resp = client.get(
            f'/api/purchase-orders/{seeded_po.id}',
            headers=auth_headers['purchaser'],
        )
        assert resp.status_code == 200
        assert resp.get_json()['code'] == 200
        data = resp.get_json()['data']
        assert data['id'] == seeded_po.id
        assert 'items' in data

    def test_get_nonexistent_po_returns_404(self, client, auth_headers):
        """PO 不存在：404"""
        resp = client.get('/api/purchase-orders/99999', headers=auth_headers['purchaser'])
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404
