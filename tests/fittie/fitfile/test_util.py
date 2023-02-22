from fittie.fitfile.util import rollover_timestamp


def test_rollover_timestamp():
    """
    Test data from FIT file documentation
    """
    initial_timestamp = 0x0000003B

    assert (
        resultant_timestamp := rollover_timestamp(initial_timestamp, 0b11101)
    ) == 0x3D

    assert (
        resultant_timestamp := rollover_timestamp(resultant_timestamp, 0b00010)
    ) == 0x42

    assert (
        resultant_timestamp := rollover_timestamp(resultant_timestamp, 0b00101)
    ) == 0x45

    assert rollover_timestamp(resultant_timestamp, 0b00001) == 0x61
