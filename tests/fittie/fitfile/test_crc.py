from fittie.fitfile.crc import calculate_checksum


def test_calculate_checksum():
    assert calculate_checksum(b'\x0e D\x08-\x86\x00\x00.FIT') == 3484
