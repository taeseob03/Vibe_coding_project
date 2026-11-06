import pytest
from app.effects import character_state
from app.progress import calculate_progress


def test_empty_state_is_neutral():
    assert character_state(calculate_progress({})) == {
        'expression': 'neutral', 'intensity': 0, 'dominant_activity': None,
    }


@pytest.mark.parametrize('category,expression', [
    ('공부','focused'), ('운동','energetic'), ('연애','heart_eyes'), ('술','relaxed'),
])
def test_display_state_uses_current_stat(category,expression):
    state=character_state(calculate_progress({category:5}))
    assert state['dominant_activity']==category
    assert state['expression']==expression and state['intensity']==2
