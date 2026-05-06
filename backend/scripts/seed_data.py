import click
import os
import sys
from flask.cli import with_appcontext
from sqlalchemy import text
from werkzeug.security import generate_password_hash
from extensions import db
from app.models import User, Role, SystemDict, Supplier, FixtureTemplate


# ---------------------------------------------------------------------------
# Reset helpers
# ---------------------------------------------------------------------------

def _reset_seed_tables():
    db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    db.session.execute(text("DELETE FROM users WHERE username = 'admin'"))
    db.session.execute(text("TRUNCATE TABLE user_roles"))
    db.session.execute(text("TRUNCATE TABLE roles"))
    db.session.execute(text("TRUNCATE TABLE system_dicts"))
    db.session.execute(text("TRUNCATE TABLE suppliers"))
    db.session.execute(text("TRUNCATE TABLE fixture_templates"))
    db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    db.session.commit()
    click.echo('✓ Seed tables reset.')


# ---------------------------------------------------------------------------
# Seed functions (idempotent upsert — insert if not exists, skip otherwise)
# ---------------------------------------------------------------------------

def seed_roles():
    ROLES = [
        ('pm',                '项目经理'),
        ('design_engineer',   '设计工程师'),
        ('me',                '制造工程'),
        ('purchaser',         '采购'),
        ('iqc',               '来料质检'),
        ('warehouse',         '仓库'),
        ('production_lead',   '生产组长'),
        ('business_engineer', '业务工程师'),
        ('management',        '管理层'),
        ('super_admin',       '超级管理员'),
    ]
    inserted = skipped = 0
    for code, name in ROLES:
        if Role.query.filter_by(code=code).first():
            skipped += 1
        else:
            db.session.add(Role(code=code, name=name))
            inserted += 1
    click.echo(f'seed_roles:             inserted={inserted}, skipped={skipped}')


def seed_super_admin():
    pwd = os.environ.get('INITIAL_ADMIN_PASSWORD')
    if not pwd:
        click.secho('INITIAL_ADMIN_PASSWORD not set in env', fg='red')
        sys.exit(1)

    if User.query.filter_by(username='admin').first():
        click.echo('seed_super_admin:       inserted=0, skipped=1')
        return

    role = Role.query.filter_by(code='super_admin').first()
    if not role:
        click.secho('super_admin role not found — ensure seed_roles() ran first', fg='red')
        sys.exit(1)

    admin = User(
        username='admin',
        full_name='超级管理员',
        password_hash=generate_password_hash(pwd),
        is_active=True,
    )
    db.session.add(admin)
    admin.roles.append(role)
    click.echo('seed_super_admin:       inserted=1, skipped=0')


def seed_statuses():
    STATUSES = [
        (1,  'pending_iqc',         '待 IQC'),
        (2,  'iqc_inspecting',      'IQC 检验中'),
        (3,  'emergency_pending',   '紧急上机待审批'),
        (4,  'concession_accepted', '让步接受'),
        (5,  'installing',          '安装调试中'),
        (6,  'acceptance_testing',  '试产验收中'),
        (7,  'in_stock',            '在库'),
        (8,  'in_use',              '使用中'),
        (9,  'maintaining',         '保养中'),
        (10, 'repairing',           '维修中'),
        (11, 'sealed',              '已封存'),
        (12, 'scrapped',            '已报废'),
    ]
    inserted = skipped = 0
    for sort, key, value in STATUSES:
        if SystemDict.query.filter_by(dict_type='fixture_status', dict_key=key).first():
            skipped += 1
        else:
            db.session.add(SystemDict(
                dict_type='fixture_status',
                dict_key=key,
                dict_value=value,
                sort_order=sort,
            ))
            inserted += 1
    click.echo(f'seed_statuses:          inserted={inserted}, skipped={skipped}')


def seed_device_codes():
    CODES = [
        (1, 'YN',   '英诺激光封边线'),
        (2, 'DZ2X', '大族 2X 封边线'),
        (3, 'DZ2S', '大族 2S 封边线'),
        (4, 'LRJ',  '狼人机'),
        (5, 'ZDY',  '中段一体机'),
        (6, 'YY',   '油压冲槽机'),
    ]
    inserted = skipped = 0
    for sort, key, value in CODES:
        if SystemDict.query.filter_by(dict_type='equipment_code', dict_key=key).first():
            skipped += 1
        else:
            db.session.add(SystemDict(
                dict_type='equipment_code',
                dict_key=key,
                dict_value=value,
                sort_order=sort,
            ))
            inserted += 1
    click.echo(f'seed_device_codes:      inserted={inserted}, skipped={skipped}')


def seed_suppliers():
    SUPPLIERS = [
        ('KFS', '科发盛', '冲压模'),
        ('HR',  '和润',   '冲压模'),
        ('HS',  '徽朔',   '冲压模'),
        ('BT',  '宝碳',   '石墨治具'),
        ('HX',  '恒芯',   '石墨治具'),
        ('JC',  '巨驰',   '石墨治具'),
        ('XW',  '兴旺',   '石墨治具'),
        ('FBW', '富邦威', '治具'),
        ('DR',  '顶熔',   '治具'),
        ('XDX', '先达兴', '治具'),
        ('XD',  '旭德',   '治具'),
    ]
    inserted = skipped = 0
    for code, name, category in SUPPLIERS:
        if Supplier.query.filter_by(code=code).first():
            skipped += 1
        else:
            db.session.add(Supplier(code=code, name=name, main_category=category))
            inserted += 1
    click.echo(f'seed_suppliers:         inserted={inserted}, skipped={skipped}')


def seed_fixture_templates():
    # (code, name, process_step, mode_label, equipment_label,
    #  applicable_products, default_lt_days, is_attachment, remark)
    TEMPLATES = [
        # === SUS VC（SUS_VC 独有 19 行 + BOTH 通用 15 行 = 34 行）===
        ('CY-GC',   '冲压件开模',                  '冲压 (CY)',               None,    '工程模',      'SUS_VC', 15,   False, '首套为工程模，验证用'),
        ('CY-LX',   '冲压件开模',                  '冲压 (CY)',               None,    '连续模',      'SUS_VC', 18,   False, '量产用连续模'),
        ('DW-M',    '激光切网治具',                '下盖切网定网 (DW)',       '手动',  None,          'SUS_VC', 8,    False, ''),
        ('DW-YD',   '圆刀切网治具',                '下盖切网定网 (DW)',       '自动',  '一部圆刀',    'BOTH',   None, False, ''),
        ('DW-AM',   '自动模具切网模',              '下盖切网定网 (DW)',       '自动',  '自动模具',    'BOTH',   10,   False, ''),
        ('DW-AJ',   '自动模具定网治具',            '下盖切网定网 (DW)',       '自动',  '自动模具',    'BOTH',   8,    False, '与 DW-AM 配套'),
        ('DW-AL',   '自动激光切网定网',            '下盖切网定网 (DW)',       '自动',  '激光自动',    'SUS_VC', 10,   False, ''),
        ('FB-M',    '激光封边治具',                '激光封边 (FB)',           '手动',  None,          'SUS_VC', 12,   False, ''),
        ('FB-DZ2X', '激光封边治具',                '激光封边 (FB)',           '半自动','大族 2X 线',  'SUS_VC', 15,   False, ''),
        ('FB-YN',   '激光封边治具',                '激光封边 (FB)',           '自动',  '英诺线',      'SUS_VC', 15,   False, ''),
        ('FB-DZ2S', '激光封边治具',                '激光封边 (FB)',           '自动',  '大族 2S 线',  'SUS_VC', 15,   False, ''),
        ('RZX',     '热整形石墨治具',              '真空热整形 (RZX)',        None,    None,          'SUS_VC', 8,    False, '单一类型'),
        ('DH',      '清洗治具（钣金）',            '钝化 (DH)',               None,    None,          'SUS_VC', 8,    False, '单一类型'),
        ('YC-M',    '封合刀',                      '一除 (YC)',               '手动',  None,          'BOTH',   8,    False, ''),
        ('YC-ZDY',  '封合刀',                      '一除 (YC)',               '自动',  '中段一体机',  'SUS_VC', 8,    False, ''),
        ('EC-M',    '二除治具',                    '二除 (EC)',               '手动',  None,          'BOTH',   7,    False, ''),
        ('ECF-M',   '二除封合刀',                  '二除 (EC)',               '手动',  None,          'BOTH',   8,    False, '封合刀独立编码'),
        ('EC-ZDY',  '二除治具',                    '二除 (EC)',               '自动',  '中段一体机',  'SUS_VC', 7,    False, ''),
        ('FK-M',    '激光封口治具',                '封口 (FK)',               '手动',  None,          'SUS_VC', 8,    False, '目前仅手动'),
        ('QW',      '鼠尾裁切模具',               '切尾 (QW)',               None,    None,          'SUS_VC', 10,   False, '单一类型'),
        ('DB',      '打扁模具',                    '打扁 (DB)',               None,    None,          'BOTH',   10,   False, '单一类型'),
        ('PM-M',    '喷码治具',                    '喷码 (PM)',               '手动',  None,          'BOTH',   7,    False, ''),
        ('PM-A',    '喷码治具',                    '喷码 (PM)',               '自动',  None,          'BOTH',   7,    False, ''),
        ('PM-QR',   '二维码等级测试仿形治具',      '喷码 (PM)',               None,    None,          'SUS_VC', 6,    False, '无手自动之分'),
        ('XN-LRJ',  '性能测试治具',                '性能测试 (XN)',           '手动',  '狼人机',      'BOTH',   6,    False, ''),
        ('XN-A',    '性能测试治具',                '性能测试 (XN)',           '自动',  None,          'BOTH',   6,    False, ''),
        ('XN-TC',   '温度校验块',                  '性能测试 (XN)',           None,    None,          'SUS_VC', 6,    True,  '附件，无手自动'),
        ('XN-TB',   '降温铜块',                    '性能测试 (XN)',           None,    None,          'SUS_VC', 6,    True,  '附件，无手自动'),
        ('XN-PC',   '位置校准块',                  '性能测试 (XN)',           None,    None,          'BOTH',   6,    True,  '附件，无手自动'),
        ('XN-SL',   '自动测试上料仓',              '性能测试 (XN)',           None,    None,          'BOTH',   7,    True,  '附件，无手自动'),
        ('WX',      '外形检具',                    '尺寸检查 (WX)',           None,    None,          'BOTH',   8,    False, '单一类型'),
        ('HF',      '滑缝检具',                    '平面度检查 (HF)',         None,    None,          'BOTH',   7,    False, '单一类型'),
        ('PMD',     '线激光平面度检具',            '平面度检查 (PMD)',        None,    None,          'SUS_VC', 10,   False, '单一类型'),
        ('HD',      '厚度检具',                    '厚度检查 (HD)',           None,    None,          'SUS_VC', 7,    False, '单一类型'),
        # === Cu VC 独有（8 行）===
        ('SK',    '蚀刻治具',               '蚀刻 (SK)',                          None,   None,       'CU_VC', 6,  False, '单一类型'),
        ('CC-YY', '冲槽模',                 '冲槽 (CC)',                          None,   '油压机',   'CU_VC', 12, False, ''),
        ('CC-A',  '冲槽上下冲头',           '冲槽 (CC)',                          '自动', '自动冲槽', 'CU_VC', 8,  False, ''),
        ('SJ',    '下盖烧网石墨治具',       '下盖铜网烧结 (SJ)',                  None,   None,       'CU_VC', 8,  False, '单一类型'),
        ('TH',    '上盖退火整平石墨治具',   '上盖整平 (TH)',                      None,   None,       'CU_VC', 8,  False, '单一类型'),
        ('DJ',    '点胶治具',               '点铜焊膏 (DJ)',                      None,   None,       'CU_VC', 8,  False, '单一类型'),
        ('QH',    '钎焊石墨治具',           '钎焊 (QH)',                          None,   None,       'CU_VC', 8,  False, '单一类型'),
        ('YTJ',   '电阻焊一体机治具',       '二除&电阻焊&裁切&打扁 (YTJ)',        '自动', None,       'CU_VC', 8,  False, '一体机含多工序'),
    ]
    assert len(TEMPLATES) == 42, f'模板数量异常: {len(TEMPLATES)}'

    inserted = skipped = 0
    for (code, name, process_step, mode_label, equipment_label,
         applicable_products, default_lt_days, is_attachment, remark) in TEMPLATES:
        if FixtureTemplate.query.filter_by(code=code).first():
            skipped += 1
        else:
            db.session.add(FixtureTemplate(
                code=code,
                name=name,
                process_step=process_step,
                mode_label=mode_label,
                equipment_label=equipment_label,
                applicable_products=applicable_products,
                default_lt_days=default_lt_days,
                is_attachment=is_attachment,
                remark=remark or None,
            ))
            inserted += 1
    click.echo(f'seed_fixture_templates: inserted={inserted}, skipped={skipped}')


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

@click.command('seed')
@click.option('--reset', is_flag=True, help='Wipe seed-managed tables and re-insert')
@with_appcontext
def seed_command(reset):
    if reset:
        _reset_seed_tables()
    seed_roles()
    seed_super_admin()
    seed_statuses()
    seed_device_codes()
    seed_suppliers()
    seed_fixture_templates()
    db.session.commit()
    click.echo('✓ Seed completed.')
