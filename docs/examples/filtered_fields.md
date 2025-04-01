# Filtered fields

Pass a fields filter into the fitfile variable to get specific fields.

```python
from fittie import decode


def main(filename: str):
    """
    Provide a message_type and optional set of field names to filter the output
    data of a direct iteration over the fitfile.
    """

    fitfiles = decode(filename)

    # Get all fields from all "session" messages
    for fitfile in fitfiles:
        for data in fitfile(message_type="session"):
            print(data)

        # Get only certain field data from all "record" messages
        for data in fitfile(
            message_type="record", fields=[
                "timestamp", 
                "heart_rate", 
                "power", 
                "distance"
            ]
        ):
            print(data)


if __name__ == "__main__":
    main("/path/to/fit/file.fit")
```