from model.utils import is_hangul

def test_is_hangul():
    assert is_hangul("한글") == True
    assert is_hangul("1") == False
    assert is_hangul("a") == False
    assert is_hangul("!") == False
    assert is_hangul("ㄱ") == False
    assert is_hangul("g") == False
    assert is_hangul("1달") == False
    assert is_hangul(" ") == False