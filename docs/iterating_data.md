# Iterating over data

## Iteration methods

There are several ways to iterate over the data messages in a FIT file:
- the 'direct' iterations over the FIT file, and interacting with the `data_messages` property.

The return type of the iterations is always a `dict` with field names as key. When interacting
with the `data_messages` property, you will have access to the `DataMessage` instances. 

### Direct iterate

The easiest way is to directly iterate over the decoded `fitfile` variable. This will
'chain' all the data messages of various types together in a single loop. The return value
will be a `dict` of field data.

```pycon
>>> from fittie import decode
>>> fitfiles = decode("/path/to/fit/file.fit")

>>> for fitfile in fitfiles:
...    for data in fitfile:
...        print(data)

{'serial_number': 1234, 'time_created': 1046114779, 'manufacturer': 260, 'type': 4}
{'timestamp': 1046119077, 'power': 204, 'heart_rate': 123, 'speed': 12500}
```

The first message is of type `file_id`, the second message is of type `record`.

###  Filtered iterate

The data messages can be filtered by message type, and optional field names, before iterating
over the fitfile. The return value will also be a `dict`, but will only contain
the fields that were provided in the filter.

```pycon
>>> from fittie import decode
>>> fitfiles = decode("/path/to/fit/file.fit")

>>> for fitfile in fitfiles:
...    for data in fitfile(message_type="record", fields=["timestamp", "power"]):
...        print(data)

{'timestamp': 1046119077, 'power': 204}
```

Only the messages of type `record` are returned, with a filter on fields `timestamp` and `power`.

#### Notes

If a filtered message type is not found, an empty list will be returned. If a filtered field does
not exist, it will be returned with value `None`.

### Accessing data messages property

The parsed FIT file has a `data_messages` property. This is a `dict` with message type keys and lists of 
`DataMessage` as values. To read the data of a `DataMessage`, access its `fields` property.

#### Helper methods and properties

The FIT file has a number of helper methods and properties to make interacting with this property a bit more convenient.

**Get a list of all available message types**
```pycon
>>> fitfile.available_message_types
['file_id', 'device_info', 'event', 'record', 'lap', 'session', 'activity']
```

**Get all messages of a specific type**
```pycon
>>> fitfile.get_messages_by_type("record")
[DataMessage(...), DataMessage(...), DataMessage(...)]
```
