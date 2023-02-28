# Highest average power

This examples shows how to get the highest average power for a given window size.

```python
from collections import deque

from fittie import decode


def main(filename: str) -> None:
    fitfile = decode(filename)

    power_data: list[int] = []

    for data in fitfile(message_type="record", fields=["power"]):
        power_data.append(data["power"])

    windows = {
        "5 seconds": 5,
        "15 seconds": 15,
        "30 seconds": 30,
        "1 minute": 1 * 60,
        "2 minutes": 2 * 60,
        "5 minutes": 5 * 60,
        "10 minutes": 10 * 60,
        "20 minutes": 20 * 60,
        "30 minutes": 30 * 60,
        "1 hour": 60 * 60,
    }

    for description, window in windows.items():
        average = get_highest_average(power_data, window)
        print(f"{description}:\t{average} watts")


def get_highest_average(data: list[int], window: int) -> int:
    """
    Get the highest average for the provided time window
    """
    sample_size = deque(data[:window], maxlen=window)
    max_average = round(sum(sample_size) / window)

    for n in data[window:]:
        sample_size.append(n)
        max_average = max(round(sum(sample_size) / window), max_average)

    return max_average


if __name__ == "__main__":
    main("/path/to/fit/file.fit")
```