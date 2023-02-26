from fittie.utils.endianness import Endianness


def test_endianness():
    assert Endianness.BIG == ">"
    assert Endianness.LITTLE == "<"


def test_endianness__str():
    assert str(Endianness.BIG) == ">"
    assert str(Endianness.LITTLE) == "<"
