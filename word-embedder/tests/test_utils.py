from utils import is_hangul_string


def test_is_hangul_string():
    assert is_hangul_string("한글")
    assert not is_hangul_string("1")
    assert not is_hangul_string("a")
    assert not is_hangul_string("!")
    assert not is_hangul_string("ㄱ")
    assert not is_hangul_string("g")
    assert not is_hangul_string("1달")
    assert not is_hangul_string(" ")
    assert not is_hangul_string("\n")
    assert not is_hangul_string("한글\n")