# fittie

Parse Garmin .FIT files

[![PyPI version](https://img.shields.io/pypi/v/fittie?color=green)](https://pypi.org/project/fittie/)

## Installation

Fittie is available on pypi and can be installed with the following command.

```shell
$ pip install fittie
```

## Example

```python
from fittie import decode

if __name__ == "__main__":
    fitfile = decode("path/to/fit/file.fit")
        
    # Example: get average heart rate
    print(fitfile.average_heart_rate)

    # Loop through all data messages:
    for data_message in fitfile:
        print(data_message)
```

For more information and examples, check [the documentation](https://marcelblijleven.github.io/fittie/)

<!-- fitfile section -->
## Fitfile

### Usage

Decoding / parsing a FIT file is done through the `decode` function in the 
`fittie.fitfile` package. It accepts the following types of arguments:

- A file path string
- A file opened in "rb" mode
- A buffered reader, BinaryIO or BytesIO

```python
# Examples
from io import BytesIO
from fittie.fitfile import decode

fitfile_1 = decode("/path/to/fit/file.fit")         # Path to file

fitfile_2 = decode(BytesIO(...))                    # BytesIO

with open("/path/to/fit/file.fit", "rb") as f:      # File opened in rb mode
    fitfile_3 = decode(f)
```

To view the available message types in the fitfile, use the `available_message_types` 
property. It will return a list of message type keys. These keys can be used to retrieve
all messages of a certain kind. After retrieving the available message types, 
the messages can be retrieved using `get_messages_by_type`.

```python
fitfile = decode("/path/to/fit/file.fit")

types = fitfile.available_message_types
# e.g. [ 'file_id', 'device_info', 'record', 'event', 'lap', 'session', 'activity']
messages = fitfile.get_messages_by_type('record')  # Returns a list of `DataMessage`
```

Alternatively, you can interact with the `messages` property of `fitfile` directly, this
is a simple dict.

#### File types

All FIT files should contain a file id message that describes the type of file. Common 
file types are `activity`, `workout` and `course`. More file types can be found in 
`fit_types.py`.

To retrieve the type of the decoded `fitfile`, use the `.file_type` property.

```pycon
assert fitfile.file_type == "activity"
```

#### CRC

A crc check is done by default, but can be disabled by providing `calculate_crc=False`
to the `decode` function to improve speed.

For example, on the same FIT file with 58297 data messages, decoding with crc takes 0.029 seconds and without
crc it only takes 0.014 seconds.

#### DataMessages

To access data in a `DataMessage`, use the `fields` property. This will return a dict
with all the values inside the message.

```python
fitfile = decode("/path/to/fit/file.fit")

for record in fitfile.get_messages_by_type("record")[:5]:
    print(record.fields)

# {'timestamp': 1044776016}
# {'timestamp': 1044776016, 'heart_rate': 117}
# {'timestamp': 1044776017, 'heart_rate': 116}
# {'timestamp': 1044776017, 'heart_rate': 115}
# {'timestamp': 1044776018, 'heart_rate': 115}
```

<!-- end fitfile section -->

## TODO:
 * Handle component fields
 * Handle accumulators
 * Handle chained FIT files
 * Handle compressed timestamps
 * move record_header into record, instead of reading it separately
 * encoding
