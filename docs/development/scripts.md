# Scripts

This page contains information about the scripts to update the FIT profile files and
README.md files.


## Parse profile

> ⚠️ This is only needed for updating the Garmin FIT SDK files. Not needed for normal 
> use of this package.

The `parse_profile.py` script takes the Profile information from the Garmin FIT SDK
and generates Python dictionaries at `fittie/profile/messages.py` and 
`fittie/profile/fit_types.py`.

Download the Garmin FIT SDK release from https://developer.garmin.com/fit/download/,
open the Profile.xlsx and save the tabs to `Types.csv` and `Messages.csv`. Place these
csv files at `scripts/data/` and run `parse_profile.py` from inside the `scripts` 
directory.

Directly generating the files from the `.xlsx` file is currently not supported.

## Compile README

> ⚠️ This is only needed for updating the main `README.md` file. Not needed for normal 
> use of this package.

The `compile_readme.py` script searches for all nested `README.md` files in the 
repository and places the content of those files inside the main `README.md`.
<!-- end scripts section -->
