# Scripts data

Place Messages.csv and Types.csv from the Garmin profile in this directory. Update 
the profile version in version.txt if necessary.

The CSV files should have the column names as first row.

If you get a key error during the parsing of messages, it is likely that a new message 
number was added. Open the Profile.xlsx and search for the missing key, and add it to
`mesg_nums.py`.
