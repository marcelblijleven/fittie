# fittie

Parse Garmin .FIT files

[![PyPI version](https://badge.fury.io/py/fittie.svg)](https://badge.fury.io/py/fittie)

```shell
pip install fittie
```

## Example

```python
from fittie.fitfile import decode

if __name__ == "__main__":
    fitfile = decode("path/to/fit/file.fit")
        
    # Example: get average heart rate
    print(fitfile.average_heart_rate)
```

<!-- fitfile section -->
## Fitfile

(Add more information about the fittie API)

### Usage

(Add usage examples and information)

### Record headers

...

### Data messages

...

### Definition messages

...

### Field definitions

...


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
 - add data/stream class
 - crc check
 - handle components, accumulators etc
 - handle chained FIT
 - compressed timestamps
 - move record_header into record, instead of reading it separately
 - encoding
