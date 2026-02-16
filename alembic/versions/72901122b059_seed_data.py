"""seed data

Revision ID: 72901122b059
Revises: 6d0943dd1662
Create Date: 2026-01-05 10:12:35.104205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '72901122b059'
down_revision: Union[str, Sequence[str], None] = '6d0943dd1662'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    clinics_table = table('clinics',
        column('id', sa.Integer),
        column('name', sa.String),
        column('address', sa.String),
        column('phone', sa.String)
    )
#    # 2. Insertar los registros de ejemplo
    op.bulk_insert(clinics_table, [
        {
            'id': 1, 
            'name': 'Clínica Kennedy Quito', 
            'address': 'Av. Amazonas y Naciones Unidas', 
            'phone': '022222222'
        },
        {
            'id': 2, 
            'name': 'Consultorio Médico Guayaquil', 
            'address': 'Puerto Santa Ana, Edif. The Point', 
            'phone': '044444444'
        }
    ])    

    doctors_table = table('doctors',
            column('id', sa.Integer),
            column('clinic_id', sa.Integer),
            column('full_name', sa.String),
            column('specialty', sa.String),
            column('phone', sa.String),
            column('email', sa.String),
            column('is_active', sa.Boolean)
        )
    op.bulk_insert(doctors_table, [
        {
            'id': 1,
            'clinic_id': 1,
            'full_name': 'Dr. Juan Pérez',
            'specialty': 'Medicina General',
            'phone': '0999999999',
            'email': 'juan.perez@miclinica.com',
            'is_active': True
        }, 
        {
            'id': 2,
            'clinic_id': 1,
            'full_name': 'Dra. María Gómez',
            'specialty': 'Pediatría',
            'phone': '0888888888',
            'email': 'maria.perez@miclinica.com',
            'is_active': True
        }       
    ])


def downgrade() -> None:
    op.execute("DELETE FROM doctors WHERE id IN (1, 2)")
    op.execute("DELETE FROM clinics WHERE id IN (1, 2)")
