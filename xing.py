import sys
import requests
import argparse
import csv
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def translate_characters(name):
    characters_mapping = {
        'Ä': 'Ae',
        'Ö': 'Oe',
        'Ü': 'Ue',
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss',
        "ã": "a",
        ";": "",
        " ": "-"
    }
    translated_name = name
    for character, replacement in characters_mapping.items():
        translated_name = translated_name.replace(character, replacement)
    return translated_name

def generate_email(first_name, last_name, domain, format_index, custom_format=None):
    formats = []
    if custom_format is not None:
        formats.append(custom_format)
    else:
        formats = [
        "{first_initial}{last_name}@{domain}",
        "{first_name}{last_initial}@{domain}",
        "{first_name}.{last_name}@{domain}",
        "{first_name}_{last_name}@{domain}",
        "{first_name}@{domain}",
        "{last_name}@{domain}"
        ]

    first_initial = first_name[0]
    last_initial = last_name[0]
    email_address = formats[format_index-1].format(first_initial=first_initial, last_initial=last_initial,first_name=first_name, last_name=last_name, domain=domain)
    return email_address

def unauthenticated_call(company, domain, format_index, custom_email, csv_separator, csv_header):
    data_list = []
    employee_url = f"https://www.xing.com/pages/{company}/employees"
    company_unauthenticated_response = requests.post(employee_url)

    if company_unauthenticated_response.status_code == 200:
        company_unauthenticated_text = company_unauthenticated_response.text
        regex = r"(?<=APOLLO_STATE=)(.*)(?=;\n.*<\/script>)"
        company_unauthenticated_json = json.loads(re.findall(regex,company_unauthenticated_text, re.DOTALL)[0])

        if csv_header:
            data_list.append([f"Email-address{csv_separator}Display-Name{csv_separator}Firstname{csv_separator}Lastname{csv_separator}Gender{csv_separator}Occupations{csv_separator}Profile-URL"])

        for key in company_unauthenticated_json.keys():
            if "xingid:" in key.lower():
                employee_data = company_unauthenticated_json[key]
                page_name = employee_data['pageName']
                profile_url = f"https://www.xing.com/profile/{page_name}"
                #employee_id = employee_data['id']
                first_name = translate_characters(employee_data['firstName'].lower())
                last_name = translate_characters(employee_data['lastName'].lower())
                display_name = employee_data['displayName']
                gender = employee_data['gender']

                occupations_all = employee_data['occupations']
                occupations_list = [occupation['subline'] for occupation in occupations_all]
                occupations = ', '.join(occupations_list)

                if custom_email is None:
                    email_address = generate_email(first_name,last_name,domain,format_index)
                else:
                    email_address = generate_email(first_name,last_name,domain,1,custom_email)

                csv_entry = [f'{email_address}{csv_separator}{display_name}{csv_separator}{first_name}{csv_separator}{last_name}{csv_separator}{gender}{csv_separator}{occupations}{csv_separator}{profile_url}']
                data_list.append(csv_entry)
    else:
        print(f">>> Company unauthenticated request failed with status code {company_unauthenticated_response.status_code}")
        sys.exit(0)

    return data_list

def get_xing_employees(company, amount, username, password, sort):
    options = Options()
    options.add_argument('--headless')  # Run ChromeDriver in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Create a new ChromeDriver instance
    driver = webdriver.Chrome(options=options)

    # Load the XING login page
    driver.get('https://login.xing.com/')

    # Find the username and password input fields and enter your credentials
    username_field = driver.find_element(By.ID, 'username')
    username_field.send_keys(username)

    password_field = driver.find_element(By.ID, 'password')
    password_field.send_keys(password)

    # Submit the login form
    password_field.send_keys(Keys.RETURN)

    # Wait for the login process to complete (adjust the timeout if needed)
    wait = WebDriverWait(driver, 10)

    wait.until(EC.any_of(EC.url_contains('www.xing.com'),EC.title_is('XING'),EC.title_contains('MFA')))

    # Once the login is successful, we grab the cookie
    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == 'login':
            login_cookie = cookie['value']

    # Remember to close the browser driver when you're done
    driver.quit()

    # URL für XING API
    api_url = 'https://www.xing.com/xing-one/api'

    headers = {
        'Content-Type': 'application/json',
    }

    company_data = {
        "operationName": "EntitySubpage",
        "variables": {
            "id": company,
            "moduleType": "employees"
        },
        "query": "query EntitySubpage($id: SlugOrID!) {entityPageEX(id: $id) { ... on EntityPage {context { companyId }}}}"}

    company_response = requests.post(api_url, headers=headers, json=company_data)

    # Check the response status code
    if company_response.status_code == 200:
        # Extract companyId from the JSON response
        json_response = company_response.json()
        company_id = json_response['data']['entityPageEX']['context']['companyId']

        headers = {
            'Content-Type': 'application/json',
            'Cookie': f'login={login_cookie}'
        }

        employee_count_request = {
                "operationName":"Employees",
                "variables":{
                    "consumer":"",
                    "includeTotalQuery":False,
                    "id":company_id,
                    "first":1,
                    "query":{
                        "consumer":"web.entity_pages.employees_subpage",
                        "sort":"CONNECTION_DEGREE"
                        }
                    },
                "query":"query Employees($id: SlugOrID!, $first: Int, $after: String, $query: CompanyEmployeesQueryInput!, $consumer: String! = \"\", $includeTotalQuery: Boolean = false) {\n  company(id: $id) {\n    id\n    totalEmployees: employees(first: 0, query: {consumer: $consumer}) @include(if: $includeTotalQuery) {\n      total\n      __typename\n    }\n    employees(first: $first, after: $after, query: $query) {\n total\n}}}"
                }

        employee_count_response = requests.post(api_url, headers=headers, json=employee_count_request)

        if employee_count_response.status_code == 200:
            json_response = employee_count_response.json()
            employee_count = json_response['data']['company']['employees']['total']

            if amount is None or amount >= 3000:
                if employee_count >= 3000:
                    amount = 2999
                else:
                    amount = employee_count

            # One could sort between LAST_NAME and CONNECTION_DEGREE
            employee_data = {
                "operationName": "Employees",
                "variables": {
                    "consumer": "",
                    "includeTotalQuery":True,
                    "id": company_id,
                    "first": amount,
                    "query": {
                        "consumer": "web.entity_pages.employees_subpage",
                        "sort": sort
                    }
                },
                "query": "query Employees($id: SlugOrID!, $first: Int, $after: String, $query: CompanyEmployeesQueryInput!, $consumer: String! = \"\", $includeTotalQuery: Boolean = false) {\n  company(id: $id) {\n    id\n    totalEmployees: employees(first: 0, query: {consumer: $consumer}) @include(if: $includeTotalQuery) {\n      total\n      __typename\n    }\n    employees(first: $first, after: $after, query: $query) {\n      total\n      edges { node {profileDetails {id firstName lastName displayName gender clickReasonProfileUrl(clickReasonId: CR_WEB_PUBLISHER_EMPLOYEES_MODULE){profileUrl} occupations {subline}}}}}}}"
            }

            employee_response = requests.post(api_url, headers=headers, json=employee_data)

            # Check the response status code
            if employee_response.status_code == 200:
                return employee_response.json()
            else:
                print(f">>> Employee request failed with status code {employee_response.status_code}")
                sys.exit(0)
        else:
            print(f">>> Employee count request failed with status code{employee_count_response.status_code}")
            sys.exit(0)
    else:
        print(f">>> Company request failed with status code {company_response.status_code}")
        sys.exit(0)

def authenticated_call(employee_response, domain, format, custom_email, csv_separator, csv_header):
    data_list = []
    employees = employee_response['data']['company']['employees']['edges']

    if csv_header:
        data_list.append([f"Email-address{csv_separator}Display-Name{csv_separator}Firstname{csv_separator}Lastname{csv_separator}Gender{csv_separator}Occupations{csv_separator}Profile-URL"])

    # Extract and print employee information
    for edge in employees:
        node = edge['node']
        profile_details = node['profileDetails']
        if profile_details['clickReasonProfileUrl']:
            profile_url = profile_details['clickReasonProfileUrl']['profileUrl']
        #employee_id = profile_details['id']

        first_name = translate_characters(profile_details['firstName'].lower())
        last_name = translate_characters(profile_details['lastName'].lower())
        display_name = profile_details['displayName']
        gender = profile_details['gender']

        occupations_all = profile_details['occupations']
        occupations_list = [occupation['subline'] for occupation in occupations_all]
        occupations = '| '.join(occupations_list)

        if custom_email is None:
            email_address = generate_email(first_name,last_name,domain,format)
        else:
            email_address = generate_email(first_name,last_name,domain,1,custom_email)

        csv_entry = [f'{email_address}{csv_separator}{display_name}{csv_separator}{first_name}{csv_separator}{last_name}{csv_separator}{gender}{csv_separator}{occupations}{csv_separator}{profile_url}']
        data_list.append(csv_entry)

    return data_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This OSINT tool was built for extracting XING employee data and generating e-mail addresses.')
    parser.add_argument('-u', '--username', type=str, help='XING username')
    parser.add_argument('-p', '--password', type=str, help='XING password')
    parser.add_argument('-c', '--company', type=str, help='The company name as found in XING')
    parser.add_argument('--amount', default=1000, type=int, help='The number of employees, default: 1000')
    parser.add_argument('-d', '--domain', help='The companies e-mail domain name')
    parser.add_argument('--format', type=int, default=3, help='The structure of the company e-mail addresses. Default: 3. Currently, the following options are available: 1 -> {first_initial}{last_name}, 2 -> {first_name}{last_initial}, 3 -> {first_name}.{last_name}, 4 -> {first_name}_{last_name}, 5 -> {first_name}, 6 -> {last_name}')
    parser.add_argument('--custom-email', type=str, help='Optional: Custom email address structure, e.g. {first_initial}{last_name}')
    parser.add_argument('-s','--sort', type=str, default='CONNECTION_DEGREE', help='XING allows sorting between LAST_NAME and CONNECTION_DEGREE')
    parser.add_argument('-o','--output', type=str, default='employees.csv', help='The name of the CSV file to save the output')
    parser.add_argument('--csv-separator', type=str, default=";", help='Desired CVS file separator, default: ";"')
    parser.add_argument("--csv-header", action="store_true", help="Include header in CSV file")
    parser.add_argument("--stdout", action="store_true", help="Print results to screen")
    args = parser.parse_args()

    if not args.company:
        print(">>> Please provide a company name as found in XING")
        sys.exit(1)
    if not args.domain:
        print(">>> Please provide a company e-mail domain")
        sys.exit(1)
    if args.format:
        if not isinstance(args.format, int):
            print(">>> Please choose the email address structure of the company by choosing between the numbers 1 to 6.")
            sys.exit(1)

    output_file = f"{args.company}_{args.output}"

    if args.custom_email:
        custom_email = args.custom_email + "@" +f"{args.domain}"
    else:
        custom_email = None

    if not args.username or not args.password:
        print(">>> No user credentials were provided, preceding with unauthenticated search, which returns up to thirty employees.")
        data_list = unauthenticated_call(args.company, args.domain, args.format, custom_email, args.csv_separator, args.csv_header)
    else:
        employee_response = get_xing_employees(args.company, args.amount, args.username, args.password, args.sort)
        data_list = authenticated_call(employee_response, args.domain, args.format, custom_email, args.csv_separator, args.csv_header)

    with open(output_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(data_list)

    if args.stdout:
        print('\n'.join(''.join(map(str,entry)) for entry in data_list))
