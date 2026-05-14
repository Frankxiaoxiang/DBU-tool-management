from unittest.mock import patch, ANY, MagicMock

from extensions import db
from app.models.fixture_template_snapshot import FixtureTemplateSnapshot
from app.services.snapshot_service import lock_snapshot, sync_missing_templates


# ─── lock_snapshot ────────────────────────────────────────────────────────────

class TestLockSnapshot:

    def test_lock_snapshot_sus_vc_returns_correct_count(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        seeded_templates(product_type='SUS_VC', count=5)
        count = lock_snapshot(seeded_project.id, seeded_pm_user.id)
        assert count == 5

    def test_lock_snapshot_creates_correct_db_rows(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        templates = seeded_templates(product_type='SUS_VC', count=5)
        lock_snapshot(seeded_project.id, seeded_pm_user.id)
        snapshots = db_session.execute(
            db.select(FixtureTemplateSnapshot).where(
                FixtureTemplateSnapshot.project_id == seeded_project.id
            )
        ).scalars().all()
        assert len(snapshots) == 5
        assert {s.source_template_id for s in snapshots} == {t.id for t in templates}

    def test_lock_snapshot_excludes_inactive_templates(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        templates = seeded_templates(product_type='SUS_VC', count=5)
        templates[0].is_active = False
        templates[1].is_active = False
        db_session.flush()
        count = lock_snapshot(seeded_project.id, seeded_pm_user.id)
        assert count == 3
        snapshots = db_session.execute(
            db.select(FixtureTemplateSnapshot).where(
                FixtureTemplateSnapshot.project_id == seeded_project.id
            )
        ).scalars().all()
        assert len(snapshots) == 3

    def test_lock_snapshot_includes_both_product_type_templates(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        """BOTH 类型模板应被 SUS_VC 项目一并锁定（覆盖 Step 1-2-2 关键 fix）。"""
        seeded_templates(product_type='SUS_VC', count=3)
        seeded_templates(product_type='BOTH', count=2)
        count = lock_snapshot(seeded_project.id, seeded_pm_user.id)
        assert count == 5


# ─── sync_missing_templates ───────────────────────────────────────────────────

class TestSyncMissingTemplates:

    def test_sync_adds_new_templates_and_writes_audit_log(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        seeded_templates(product_type='SUS_VC', count=3)
        lock_snapshot(seeded_project.id, seeded_pm_user.id)
        seeded_templates(product_type='SUS_VC', count=2)

        with patch('app.services.snapshot_service.current_app') as mock_ca:
            mock_ca.logger.info = MagicMock()  # Python 3.13 会自动生成 AsyncMock，强制改回同步
            result = sync_missing_templates(seeded_project.id, seeded_pm_user.id)

        assert result['added_count'] == 2
        assert len(result['added_codes']) == 2
        mock_ca.logger.info.assert_called_once_with(
            "sync_templates action=%s operator_id=%s project_id=%s added=%d codes=%s",
            'sync_templates', seeded_pm_user.id, seeded_project.id, 2, ANY,
        )

    def test_sync_no_duplicate_for_existing_templates(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        seeded_templates(product_type='SUS_VC', count=5)
        lock_snapshot(seeded_project.id, seeded_pm_user.id)

        count_before = db_session.execute(
            db.select(db.func.count()).select_from(FixtureTemplateSnapshot).where(
                FixtureTemplateSnapshot.project_id == seeded_project.id
            )
        ).scalar()
        result = sync_missing_templates(seeded_project.id, seeded_pm_user.id)
        count_after = db_session.execute(
            db.select(db.func.count()).select_from(FixtureTemplateSnapshot).where(
                FixtureTemplateSnapshot.project_id == seeded_project.id
            )
        ).scalar()

        assert result['added_count'] == 0
        assert count_before == count_after

    def test_sync_excludes_inactive_new_templates(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        seeded_templates(product_type='SUS_VC', count=3)
        lock_snapshot(seeded_project.id, seeded_pm_user.id)
        new_templates = seeded_templates(product_type='SUS_VC', count=1)
        new_templates[0].is_active = False
        db_session.flush()

        result = sync_missing_templates(seeded_project.id, seeded_pm_user.id)
        assert result['added_count'] == 0

    def test_sync_after_create_returns_zero_no_audit_log(
        self, db_session, seeded_project, seeded_pm_user, seeded_templates
    ):
        """added_count=0 时函数提前 return，审计日志不写入。"""
        seeded_templates(product_type='SUS_VC', count=5)
        lock_snapshot(seeded_project.id, seeded_pm_user.id)

        with patch('app.services.snapshot_service.current_app') as mock_ca:
            mock_ca.logger.info = MagicMock()  # 与 test_sync_adds 保持一致，避免 AsyncMock 警告
            result = sync_missing_templates(seeded_project.id, seeded_pm_user.id)

        assert result['added_count'] == 0
        mock_ca.logger.info.assert_not_called()


# ─── POST /api/projects/:id/sync-templates ────────────────────────────────────

class TestSyncTemplatesEndpoint:

    def test_sync_endpoint_super_admin_returns_200(
        self, client, db_session, seeded_project, auth_headers
    ):
        res = client.post(
            f'/api/projects/{seeded_project.id}/sync-templates',
            headers=auth_headers['super_admin'],
        )
        assert res.status_code == 200
        data = res.get_json()['data']
        assert 'added_count' in data
        assert 'added_codes' in data

    def test_sync_endpoint_pm_returns_403(
        self, client, seeded_project, auth_headers
    ):
        res = client.post(
            f'/api/projects/{seeded_project.id}/sync-templates',
            headers=auth_headers['pm'],
        )
        assert res.status_code == 403
        assert res.get_json()['code'] == 403

    def test_sync_endpoint_iqc_returns_403(
        self, client, seeded_project, auth_headers
    ):
        res = client.post(
            f'/api/projects/{seeded_project.id}/sync-templates',
            headers=auth_headers['iqc'],
        )
        assert res.status_code == 403
        assert res.get_json()['code'] == 403

    def test_sync_endpoint_project_not_found_returns_404(
        self, client, auth_headers
    ):
        res = client.post(
            '/api/projects/99999/sync-templates',
            headers=auth_headers['super_admin'],
        )
        assert res.status_code == 404
        assert res.get_json()['code'] == 404
