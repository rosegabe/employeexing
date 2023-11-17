# xing-employeezing
A simple python script that iterates over the employees of a given company on XING and returns CSV output containing e-mail addresses, first names, last names, occupation and profile URL information.

## Setup

pip3 install -r requirements.txt

#### Install of chrome and chromedriver
- Update your packages: ``sudo apt update``
- Download and install chrome: ``wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb``
- Install chrome from the downloaded file: ``sudo dpkg -i google-chrome-stable_current_amd64.deb`` and ``sudo apt-get install -f``
- Check Chrome is installed correctly: ``google-chrome --version``

This version is important, you will need it to get the correct verison for chromedriver.
- Download chromedriver as a .zip from https://chromedriver.chromium.org/downloads according to your current chrome version.
- Unzip and move chromedriver binary to the current folder in which xing.py resided.

## Usage

```bash
usage: xing.py [-h] [-u USERNAME] [-p PASSWORD] [-c COMPANY] [--amount AMOUNT] [-d DOMAIN] [--format FORMAT]
               [--custom-email CUSTOM_EMAIL] [-s SORT] [-o OUTPUT] [--csv-separator CSV_SEPARATOR] [--csv-header]
               [--stdout] [--double-name-separator DOUBLE_NAME_SEPARATOR]

This OSINT tool was built for extracting XING employee data and generating e-mail addresses.

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        XING username
  -p PASSWORD, --password PASSWORD
                        XING password
  -c COMPANY, --company COMPANY
                        The company name as found in XING
  --amount AMOUNT       The number of employees, default: 1000
  -d DOMAIN, --domain DOMAIN
                        The companies e-mail domain name
  --format FORMAT       The structure of the company e-mail addresses. Default: 3. Currently, the following
                        options are available: 1 -> {first_initial}{last_name}, 2 -> {first_name}{last_initial}, 3
                        -> {first_name}.{last_name}, 4 -> {first_name}_{last_name}, 5 -> {first_name}, 6 ->
                        {last_name}
  --custom-email CUSTOM_EMAIL
                        Optional: Custom email address structure, e.g. {first_initial}{last_name}
  -s SORT, --sort SORT  XING allows sorting between LAST_NAME and CONNECTION_DEGREE
  -o OUTPUT, --output OUTPUT
                        The name of the CSV file to save the output
  --csv-separator CSV_SEPARATOR
                        Desired CVS file separator, default: ";"
  --csv-header          Include header in CSV file
  --stdout              Print results to screen
  --double-name-separator DOUBLE_NAME_SEPARATOR
                        Desired separator for double names, default: "-"
```
