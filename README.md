# vendor-file-cli
CLI tool to retrieve files from vendor servers.

## Setup
### Install with pip
1. Create a folder: `$ mkdir vendor-file-cli`
2. Navidate to folder: `$ cd vendor-file-cli`
3. Create a virtual environment and activate it: 
   `$ python -m venv .venv & $ source ./.venv/scripts/activate`
4. Install from Github:
   `$ pip install git+https://github.com/BookOps-CAT/vendor-file-cli`


### Install with Poetry
1. Clone repository
2. Navigate to project directory in terminal
3. Activate virtual environment in poetry with `$ poetry shell`
4. Install dependencies with `$ poetry install`



## Usage
```
$ fetch all-vendor-files
```

This project provides a command line interface to connect to and retrieve files from vendors using FTP/SFTP. Files are copied to the vendor's directory on BookOps' NSDROP SFTP server. Credentials are read from a local `yaml` file or environment variables. 

This CLI can also validate MARC records using the models defined in [record-validator](https://github.com/BookOps-CAT/record-validator). Currently this tool is able to validate records for Eastview, Leila, and Amalivre (SASB). 

### Commands
The following information is also available using `validator --help`

#### Available commands

##### Retrieve all new files
`$ fetch all-vendor-files`

Retrieves all new files for all vendors with configured credentials. 
 - Logs into each vendor's server, 
 - Creates a lists of files on the server and in the corresponding directory on NSDROP,
 - Copies all files from the vendor's server that are not in the NSDROP directory, 
 - For select vendors the records will be validated before they are copied to NSDROP
   - Currently these vendors are Eastview, Leila, and Amalivre (SASB) 
   - The validation output is written to a [google sheet](https://docs.google.com/spreadsheets/d/1ZYuhMIE1WiduV98Pdzzw7RwZ08O-sJo7HJihWVgSOhQ/edit?usp=sharing).

##### List all vendors configured to work with CLI
`$ fetch available-vendors`

Prints a list of vendors with credentials configured to work with the CLI.

##### Validate vendor .mrc files
`$ fetch validate-file`
 - `-v`/`--vendor` vendor whose files you would like to validate

Validates files for the vendor specified using the `-v`/`--vendor` option. 

##### Retrieve files for a specified vendor within a specific timeframe

`$ fetch vendor-files`
 - `-v`/`--vendor` vendor whose files you would like to validate
 - `-d`/`--day` number of days to go back and retrieve files from
 - `-h`/`--hour` number of hours to go back and retrieve files from

Retrieves files for a specified vendor within the specified timeframe. If neither `--day` nor `--hour` is provided, all files will be retrieved. If the file already exists in the corresponding directory on NSDROP, it will be skipped. Command accepts multiple args passed to `-v`/`--vendor`, eg. to fetch files from Eastview and Leila created within the last 10 days:
   `$ fetch vendor-files -v eastview -v leila -d 10`
