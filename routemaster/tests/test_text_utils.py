from pytest import raises

from routemaster.text_utils import join_comma_or


def test_join_comma_or_no_items():
    with raises(ValueError):
        join_comma_or([])


def test_join_comma_or_single_item():
    actual = join_comma_or(['item'])
    assert actual == 'item'


def test_join_comma_or_two_items():
    actual = join_comma_or(['a', 'b'])
    assert actual == 'a or b'


def test_join_comma_or_three_items():
    actual = join_comma_or(['a', 'b', 'c'])
    assert actual == 'a, b or c'


def test_join_comma_or_four_items():
    actual = join_comma_or(['a', '4', 'b', 'c'])
    assert actual == 'a, 4, b or c'
