from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from a12_ppt.models import TeacherPreferencesRequest
from a12_ppt.outline_chat.postgres_store import PostgresOutlineMemoryStore


@pytest.mark.parametrize('row, expected', [
    (None, ['group_discussion', 'quiz']),
    (({'teaching_style': 'heuristic', 'interaction_forms': []},), []),
])
def test_read_preferences_defaults_only_if_absent(row, expected):
    store = PostgresOutlineMemoryStore()
    connection = MagicMock()
    connection.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = row
    with patch('psycopg.connect', return_value=connection):
        result = store.get_teacher_preferences('teacher1')
    assert result['interaction_forms'] == expected
    assert result['teaching_style'] == (row[0]['teaching_style'] if row else '')


def test_unknown_preference_values_are_rejected():
    with pytest.raises(ValidationError):
        TeacherPreferencesRequest(teaching_style='invalid')
    with pytest.raises(ValidationError):
        TeacherPreferencesRequest(interaction_forms=['unknown'])


def test_database_failure_is_not_disguised_as_default_preferences():
    with patch('psycopg.connect', side_effect=RuntimeError('database unavailable')):
        with pytest.raises(RuntimeError):
            PostgresOutlineMemoryStore().get_teacher_preferences('teacher1')
