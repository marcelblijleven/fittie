# Utils

## Enrich data

The field data is not mapped to a value in the FIT SDK, for example when the
field name is "sport", the value can be "2" and not "cycling".

To map data to the FIT SDK and convert timestamps to utc-aware datetimes, use
the `enrich_data` util. This will edit the field dict in place with the 
new data.

```pycon
from fittie.utils import enrich_data

...

>>> data_message.fields
{'timestamp': 1045945633}
>>> enrich_data(data_message.fields)
>>> data_mesage.fields
{'timestamp': datetime.datetime(2023, 2, 21, 20, 27, 13, tzinfo=datetime.timezone.utc)}

>>> data_message.fields
{'language': 8}
>>> enrich_data(data_message.fields)
>>> data_mesage.fields
{'language': 'dutch'}
```