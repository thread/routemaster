from routemaster.utils import dict_merge


def test_dict_merge_simple():
    d1 = {'foo': 'bar'}
    d2 = {'baz': 'quux'}
    assert dict_merge(d1, d2) == {'foo': 'bar', 'baz': 'quux'}


def test_dict_merge_deep():
    d1 = {'foo': {'bar': {'baz': 1}}}
    d2 = {'foo': {'bar': {'x': 2}}}
    assert dict_merge(d1, d2) == {'foo': {'bar': {'baz': 1, 'x': 2}}}


def test_dict_merge_d2_priority():
    d1 = {'foo': {'bar': {'baz': 1}}}
    d2 = {'foo': {'bar': {'baz': 3}}}
    assert dict_merge(d1, d2) == {'foo': {'bar': {'baz': 3}}}
