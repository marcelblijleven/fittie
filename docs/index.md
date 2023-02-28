# Fittie

Fittie is a fast and simple FIT file analyser. 
The FIT (Flexible and Interoperable Data Transfer) protocol is a format designed for 
storing and sharing sports and health related data.

More information on FIT can be found in the [FIT SDK](https://developer.garmin.com/fit/protocol/) on Garmin's developer website.

## Installation

Fittie is available on Pypi and can be installed through pip.

```shell
pip install fittie
```

## Quick start

The easiest way to get started with Fittie, is by decoding a FIT file using the `decode`
function and iterating over the parsed data.

```python
from fittie import decode


def main(filename: str):
    fitfile = decode(filename)
    
    for data in fitfile:
        print(data)
    
        
if __name__ == "__main__":
    main(filename="/path/to/fit/file.fit")

```

Example output for the example above would be:

```text
...
{'timestamp': 1046116016, 'distance': 1143204, 'heart_rate': 131, 'altitude': 2566, 'speed': 12560, 'power': 214, 'cadence': 92}
{'timestamp': 1046116017, 'distance': 1144452, 'heart_rate': 131, 'altitude': 2566, 'speed': 12350, 'power': 214, 'cadence': 92}
{'timestamp': 1046116018, 'distance': 1145672, 'heart_rate': 131, 'altitude': 2567, 'speed': 12131, 'power': 216, 'cadence': 91}
...
```

See [iterating over data](iterating_data.md) for more information, and ways, to iterate
over data in a FIT file.
