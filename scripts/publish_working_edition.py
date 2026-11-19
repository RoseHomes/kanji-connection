"""Publish the verified working edition, atomically, after checking public projections."""
import json
import sys
from pathlib import Path

from sqlalchemy import text, update
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings
from app.content_revision import digest
from app.database import create_database_engine
from app.editorial_sync import TABLES, require_private, snapshot
from app.learning_presentation import comparison_groups, practice
from app.repository import DatabaseRepository


def main():
    settings = Settings().model_copy(update={"expose_samples": False, "enable_user_writes": False, "development_user_ids": []})
    receipt = json.loads((ROOT / "private/editorial-sync/2026-11-19-final-v2/committed.json").read_bytes())
    engine = create_database_engine(settings)
    try:
        with engine.connect() as connection:
            tx = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                connection.execute(text("SET LOCAL lock_timeout='10s'"))
                connection.execute(text("SET LOCAL statement_timeout='60s'"))
                connection.execute(text("SELECT pg_advisory_xact_lock(73911, 30)"))
                before = snapshot(connection, lock=True)
                require_private(before)
                if digest(before) != receipt["after_sha256"]:
                    raise ValueError("Live edition does not match the verified working revision")
                if [x['chapter'] for x in before['lessons']] != list(range(1, 31)):
                    raise ValueError("Unexpected chapter identities")
                policies = connection.execute(text("SELECT tablename FROM pg_policies WHERE schemaname='public' AND tablename = ANY(:names)"), {"names": list(TABLES)}).all()
                if policies:
                    raise ValueError("Educational tables have direct public policies; inspect before release")
                counts = {}
                for name, table in TABLES.items():
                    changes = {}
                    if 'status' in table.c: changes['status'] = 'published'
                    if 'review_status' in table.c: changes['review_status'] = 'published'
                    if 'access_tier' in table.c: changes['access_tier'] = 'free'
                    if 'catalog_visible' in table.c: changes['catalog_visible'] = True
                    if changes and before[name]:
                        result = connection.execute(update(table).values(**changes))
                        if result.rowcount != len(before[name]): raise ValueError('Unexpected publication row count')
                        counts[name] = result.rowcount
                session = Session(bind=connection, autoflush=False)
                repo = DatabaseRepository(session, False)
                catalog = repo.lessons(limit=100)
                if len(catalog) != 30: raise ValueError('Public catalog is incomplete')
                for lesson in catalog:
                    detail = repo.lesson(lesson.slug)
                    questions = practice(session, settings, None, lesson.slug)
                    if len(detail.kanjis) != 14 or len(detail.sections) != 7 or len(questions) != 15:
                        raise ValueError('Public lesson or quiz is incomplete: ' + lesson.slug)
                if len(comparison_groups(session, settings, None)) != 94:
                    raise ValueError('Public comparison groups are incomplete')
                after = snapshot(connection)
                tx.commit()
            except BaseException:
                tx.rollback()
                raise
        output = {'revision': '2026-11-19-final-v2', 'committed': True, 'counts': counts, 'before_sha256': digest(before), 'after_sha256': digest(after), 'chapters_verified': 30, 'questions_verified': 450, 'comparison_groups_verified': 94, 'account_writes_enabled': False}
        folder = ROOT / 'private/publication-release'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'receipt.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(output))
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'stopped': True, 'type': type(exc).__name__, 'reason': str(exc) if type(exc) is ValueError else 'Database details suppressed'}))
        raise SystemExit(1) from None
