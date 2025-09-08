from utils import is_hangul_string

def test_is_hangul_string():
    assert is_hangul_string("한글") == True
    assert is_hangul_string("1") == False
    assert is_hangul_string("a") == False
    assert is_hangul_string("!") == False
    assert is_hangul_string("ㄱ") == False
    assert is_hangul_string("g") == False
    assert is_hangul_string("1달") == False
    assert is_hangul_string(" ") == False
    assert is_hangul_string("\n") == False
    assert is_hangul_string("한글\n") == False