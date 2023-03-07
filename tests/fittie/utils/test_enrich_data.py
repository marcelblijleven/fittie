import pytest

from datetime import datetime, timezone

from fittie.utils.enrich_data import enrich_data


@pytest.mark.parametrize("data,expected", [
    ({"timestamp": 1045945633}, {"timestamp": datetime(2023, 2, 21, 20, 27, 13, tzinfo=timezone.utc)}),
    ({"heart_rate": 140, "manufacturer": 255}, {"heart_rate": 140, "manufacturer": "development"}),
    ({"language": 8}, {"language": "dutch"}),
    ({"i_do_not_exist": 1337}, {"i_do_not_exist": 1337}),
    ({"time_zone": 40}, {"time_zone": "amsterdam"}),
])
def test_enrich_data(data, expected):
    enrich_data(data)
    assert data == expected
