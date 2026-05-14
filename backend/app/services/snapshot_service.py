from flask import current_app
from sqlalchemy import or_

from extensions import db
from app.models.fixture_template import FixtureTemplate
from app.models.fixture_template_snapshot import FixtureTemplateSnapshot
from app.models.project import Project
from app.exceptions import NotFoundError, ValidationError


def lock_snapshot(project_id, operator_id):
    """项目创建瞬间锁定模板快照。不自行 commit，由调用方统一提交。"""
    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError('项目不存在')

    if FixtureTemplateSnapshot.query.filter_by(project_id=project_id).first():
        raise ValidationError('项目快照已存在，请勿重复锁定')

    templates = FixtureTemplate.query.filter(
        or_(
            FixtureTemplate.applicable_products == project.product_type,
            FixtureTemplate.applicable_products == 'BOTH'
        ),
        FixtureTemplate.is_active == True
    ).all()

    snapshots = [
        FixtureTemplateSnapshot(
            project_id=project_id,
            source_template_id=template.id,
            fixture_type_code=template.code,
            product_type=template.applicable_products,
            default_lt_days=template.default_lt_days,
            default_iqc_interval_days=None,
            default_install_interval_days=None,
            default_acceptance_interval_days=None,
            default_handover_interval_days=None,
            default_maintenance_threshold=None,
            synced_by=operator_id,
        )
        for template in templates
    ]
    db.session.add_all(snapshots)
    return len(snapshots)


def sync_missing_templates(project_id, operator_id):
    """追加同步新增模板到已有项目快照。严禁覆盖已有快照（CLAUDE.md §e.8 红线）。"""
    project = db.session.get(Project, project_id)
    if not project:
        raise NotFoundError('项目不存在')

    existing_codes = set(
        db.session.execute(
            db.select(FixtureTemplateSnapshot.fixture_type_code)
            .where(FixtureTemplateSnapshot.project_id == project_id)
        ).scalars().all()
    )

    all_templates = FixtureTemplate.query.filter(
        or_(
            FixtureTemplate.applicable_products == project.product_type,
            FixtureTemplate.applicable_products == 'BOTH'
        ),
        FixtureTemplate.is_active == True
    ).all()

    new_templates = [t for t in all_templates if t.code not in existing_codes]

    if not new_templates:
        return {'added_count': 0, 'added_codes': []}

    new_snapshots = [
        FixtureTemplateSnapshot(
            project_id=project_id,
            source_template_id=template.id,
            fixture_type_code=template.code,
            product_type=template.applicable_products,
            default_lt_days=template.default_lt_days,
            default_iqc_interval_days=None,
            default_install_interval_days=None,
            default_acceptance_interval_days=None,
            default_handover_interval_days=None,
            default_maintenance_threshold=None,
            synced_by=operator_id,
        )
        for template in new_templates
    ]
    db.session.add_all(new_snapshots)
    db.session.commit()

    added_codes = [t.code for t in new_templates]
    added_count = len(added_codes)

    current_app.logger.info(
        "sync_templates action=%s operator_id=%s project_id=%s added=%d codes=%s",
        'sync_templates', operator_id, project_id, added_count, added_codes
    )
    # TODO(Phase 6): migrate to audit_logs table (action/operator_id/project_id/payload)

    return {'added_count': added_count, 'added_codes': added_codes}
