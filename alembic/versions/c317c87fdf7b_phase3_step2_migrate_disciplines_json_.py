"""phase3_step2_migrate_disciplines_json_to_relational

Revision ID: c317c87fdf7b
Revises: 99548d10fc10
Create Date: 2026-01-23 18:32:09.222062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base


# revision identifiers, used by Alembic.
revision: str = 'c317c87fdf7b'
down_revision: Union[str, Sequence[str], None] = 'create_program_disciplines_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate disciplines from JSON to program_disciplines junction table."""
    bind = op.get_bind()
    Session = sessionmaker(bind=bind)
    session = Session()

    try:
        base = automap_base()
        base.prepare(autoload_with=bind)
        Program = base.classes.programs
        ProgramDiscipline = base.classes.program_disciplines

        programs = session.query(Program).filter(Program.disciplines_json != None).all()

        for program in programs:
            disciplines = program.disciplines_json
            if disciplines and isinstance(disciplines, list):
                for disc in disciplines:
                    discipline_type = disc.get('discipline')
                    weight = disc.get('weight')
                    if discipline_type and weight is not None:
                        existing = session.query(ProgramDiscipline).filter_by(
                            program_id=program.id,
                            discipline_type=discipline_type
                        ).first()
                        if not existing:
                            new_disc = ProgramDiscipline(
                                program_id=program.id,
                                discipline_type=discipline_type,
                                weight=weight
                            )
                            session.add(new_disc)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    """Rollback: remove migrated data from program_disciplines."""
    bind = op.get_bind()
    op.execute("""
        DELETE FROM program_disciplines
        WHERE program_id IN (
            SELECT id FROM programs WHERE disciplines_json IS NOT NULL
        )
    """)
