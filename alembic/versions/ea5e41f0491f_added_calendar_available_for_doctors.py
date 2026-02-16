"""added calendar available for doctors

Revision ID: ea5e41f0491f
Revises: 72901122b059
Create Date: 2026-01-12 18:53:44.662103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import datetime

# revision identifiers, used by Alembic.
revision: str = 'ea5e41f0491f'
down_revision: Union[str, Sequence[str], None] = '72901122b059'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    doctors_table = table('doctor_schedules',
            column('id', sa.Integer),
            column('doctor_id', sa.Integer),
            column('day_of_week', sa.Integer),
            column('start_time', sa.Time),
            column('end_time', sa.Time),
            column('is_blocked', sa.Boolean),   
            column('description', sa.String)
        )
    #Doctor Juan Pérez disponible de Martes yJueves de 8am a 5pm
    op.bulk_insert(doctors_table, [
        {
            'id': 1,
            'doctor_id': 1,
            'day_of_week': 1,  # Lunes
            'start_time': datetime.time(8, 0),
            'end_time': datetime.time(17, 00),
            'is_blocked': False,
            'description': 'Lunes'            
        },
        #{
        #    'id': 2,
        #    'doctor_id': 1,
        #    'day_of_week': 2,  # Martes
        #    'start_time': datetime.time(8, 0),
        #    'end_time': datetime.time(17, 00),
        #    'is_blocked': False,
        #    'description': 'Martes'            
        #},
        #{
        #    'id': 3,
        #    'doctor_id': 1,
        #    'day_of_week': 3,  # Miercoles
        #    'start_time': datetime.time(8, 0),
        #    'end_time': datetime.time(17, 00),
        #    'is_blocked': False,
        #    'description': 'Miercoles'            
        #},
        {
            'id': 4,
            'doctor_id': 1,
            'day_of_week': 4,  # Jueves
            'start_time': datetime.time(8, 0),
            'end_time': datetime.time(17, 00),
            'is_blocked': False,
            'description': 'Jueves'            
        }
        #{
        #    'id': 5,
        #    'doctor_id': 1,
        #    'day_of_week': 5,  # Viernes
        #    'start_time': datetime.time(8, 0),
        #    'end_time': datetime.time(17, 00),
        #    'is_blocked': False,
        #    'description': 'Viernes'            
        #}
    ])

    #Doctora Maria Gomez disponible de Lunes Miercoles y  Viernes de 8am a 3pm
    op.bulk_insert(doctors_table, [
        {
            'id': 6,
            'doctor_id': 2,
            'day_of_week': 1,  # Lunes
            'start_time': datetime.time(8, 0),
            'end_time': datetime.time(15, 00),
            'is_blocked': False,
            'description': 'Lunes'            
        },
        {
            'id': 7,
            'doctor_id': 2,
            'day_of_week': 3,  # Miercoles
            'start_time': datetime.time(8, 0),
            'end_time': datetime.time(15, 00),
            'is_blocked': False,
            'description': 'Miercoles'            
        },
        {
            'id': 8,
            'doctor_id': 2,
            'day_of_week': 5,  # Viernes
            'start_time': datetime.time(8, 0),
            'end_time': datetime.time(15, 00),
            'is_blocked': False,
            'description': 'Viernes'            
        }
    ])


def downgrade() -> None:
    op.execute("DELETE FROM doctor_schedules WHERE id IN (1, 2, 3, 4, 5, 6, 7, 8)")    
