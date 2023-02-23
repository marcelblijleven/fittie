# Profile

> ⚠️ This is info is mainly needed for development

The profile directory contains field information and parsed data from the Global FIT Profile,
parsed by the script located at `scripts/parse_profile.py`.

## Data

### Base types

Contains all FIT base types and their relevant information, such as data type, struct
format and size. The BaseType class has a helper method to retrieve a value from the 
provided BinaryIO.

### Fit types

Auto generated file containing information about FIT types and a mapping between value
numbers and value names. The source data of this file is the Types.csv document from 
the Garmin FIT sdk.

### Message numbers

Contains a mapping between message number and message type name.

### Message profile

Contains helper dataclasses to make working with message definitions from the Garmin FIT
sdk easier. See Messages.

### Messages

Auto generated file which contains information about messages and their fields. The 
source data of this file is the Messages.csv document from the Garmin FIT sdk.