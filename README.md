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

#### Debug

To print debug log messages, run your script with `LOGLEVEL=DEBUG` env variable.
<!-- end fitfile section -->

<!-- profile section -->
## Profile

> ⚠️ This is info is mainly needed for development

The profile directory contains field information and parsed data from the Global FIT Profile,
parsed by the script located at `scripts/parse_profile.py`.

### Data

#### Base types

Contains all FIT base types and their relevant information, such as data type, struct
format and size. The BaseType class has a helper method to retrieve a value from the 
provided BinaryIO.

#### Fit types

Auto generated file containing information about FIT types and a mapping between value
numbers and value names. The source data of this file is the Types.csv document from 
the Garmin FIT sdk.

#### Message numbers

Contains a mapping between message number and message type name.

#### Message profile

Contains helper dataclasses to make working with message definitions from the Garmin FIT
sdk easier. See Messages.

#### Messages

Auto generated file which contains information about messages and their fields. The 
source data of this file is the Messages.csv document from the Garmin FIT sdk.
<!-- end profile section -->

<!-- scripts section -->
## Scripts

These scripts can help during development of this package, they're not included in the
Pypi build.

### Parse profile

> ⚠️ This is only needed for updating the Garmin FIT SDK files. Not needed for normal 
> use of this package.

The `parse_profile.py` script takes the Profile information from the Garmin FIT SDK
and generates Python dictionaries at `fittie/fitfile/profile/messages.py` and 
`fittie/fitfile/profile/fit_types.py`.

Download the Garmin FIT SDK release from https://developer.garmin.com/fit/download/,
open the Profile.xlsx and save the tabs to `Types.csv` and `Messages.csv`. Place these
csv files at `scripts/data/` and run `parse_profile.py` from inside the `scripts` 
directory.

Directly generating the files from the `.xlsx` file is currently not supported.

### Compile README

> ⚠️ This is only needed for updating the main `README.md` file. Not needed for normal 
> use of this package.

The `compile_readme.py` script searches for all nested `README.md` files in the 
repository and places the content of those files inside the main `README.md`.
<!-- end scripts section -->

## TODO:
 - handle components, accumulators etc
 - handle chained FIT
 - compressed timestamps
 - move record_header into record, instead of reading it separately
 - encoding
