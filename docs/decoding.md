# Decoding

Decoding a FIT file can be done with the `decode` function from the Fittie package.
To make it easier, it accepts various argument types as "source".

- A path to file
- A file, opened in `rb` mode. E.g a BufferedReader
- A Streamable variable (more information about this later)

## Sources

### Path to file

```python
from fittie import decode
fitfile = decode("/path/to/fit/file.fit")
```

By providing a path to a file, the file will be automatically opened in `rb` mode and 
closed when the decoding is finished. If the provided file path does not exist, a 
FileNotFound error will be raised.

### File

```python
from fittie import decode

with open("/path/to/fit/file.fit", "rb") as file:
    fitfile = decode(file)
```

When providing an open file, the mode will be checked. If it is not `rb`, an IOError will
be raised. It is not necessary to open the file through a context manager like in the 
example. A regular call to `open()` will work too, the decoder will automatically 
close the file when finished.

### Streamable

```python
from io import BytesIO
from fittie import decode

data = BytesIO(b"example byte string")
fitfile = decode(data)
```

The Streamable protocol allows variables to be implicitly typed as a Streamable when it
implements a `tell`, `read` and `close` method. This is a subset of all the methods a
`BinaryIO` type implements.

## Crc

A crc will be calculated by default for each byte that is read during decoding, this 
calculated crc is then checked against the crc at the end of the FIT file. To make the
decoding faster (usually around 2x faster), the crc check can be disabled. 

> ⚠️ Disabling the crc check means the decoder can't verify if all the data is correct.

```python
fitfile = decode("/path/to/fit/file.fit", calculate_crc=False)
```

## FitFile

The return type of `decode` is the `FitFile` class. This class exposes several methods
and properties which the user can access, like a collection of list of `DataMessage`.

More information about iteration over these lists of `DataMessage` can be found [here](iterating_data.md).

## Decode file type

If you're only interested in reading the file type, use the `decode_file_type` function.
It assumes the FIT file is encoded according to the protocol's best practices and begins 
with the following structure:
* A file header
* A file_id definition message
* A file_id data message

If not, it will raise a `DecodeException` and no data will be returned.

```python
from fittie.fitfile.decode import decode_file_type

file_type = decode_file_type("/path/to/fit/file.fit")
```
