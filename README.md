# fittie

Parse Garmin .FIT files

## Usage

```python
from fittie.fitfile import decode

if __name__ == "__main__":
    with open("path/to/fit/file.fit", "rb") as data:
        fitfile = decode(data)
        
        # Example: get average heart rate
        print(fitfile.average_heart_rate)
```

### Debug

To print debug log messages, run your script with `LOGLEVEL=DEBUG` env variable.

## TODO:
 - Get values by native number instead of name
 - crc check
 - handle components, accumulators etc
 - handle chained FIT
 - compressed timestamps
 - move record_header into record, instead of reading it separately
 - encoding
