# Normalized power

Information about normalized power can be found at the [TrainingPeaks](https://www.trainingpeaks.com/learn/articles/normalized-power-intensity-factor-training-stress/) website.

```python
from collections import deque

from fittie import decode


def main(filename: str) -> None:
    fitfile = decode(filename)

    power_data: list[int] = []

    for data in fitfile(message_type="record", fields=["power"]):
        # Add only non-zero values to power_data
        if power := data.get("power"):
            power_data.append(power)

    print(get_normalized_power(power_data))

    
def get_moving_averages(data: list[int]) -> list[int]:
    """
    Get the moving / rolling averages of the provided data with a window size
    of 30 seconds.
    """
    window_size = 30
    moving_averages = []
    sample_size = deque(data[:window_size], maxlen=window_size)
    moving_averages.append(round(sum(sample_size) / window_size))

    for n in data[30:]:
        sample_size.append(n)
        moving_averages.append(round(sum(sample_size) / window_size))

    return moving_averages
    

def get_normalized_power(power_data: list[int]) -> int:
    """
    Get normalized power of the provided power data
    """
    data = [pow(n, 4) for n in get_moving_averages(power_data)]
    average = sum(data) / len(data)
    normalized_power = pow(average, 0.25)
    return round(normalized_power)


if __name__ == "__main__":
    main("/path/to/fit/file.fit")
```