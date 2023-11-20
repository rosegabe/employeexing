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
from unidecode import unidecode

def translate_characters(name, args):
    characters_mapping = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss',
        ";": ""
    }
    translated_name = name.lower()
    if " " in name:
        translated_name = translated_name.replace(" ", args.double_name_separator)
    for character, replacement in characters_mapping.items():
        translated_name = translated_name.replace(character, replacement)

    return unidecode(translated_name)

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
                first_name = translate_characters(employee_data['firstName'].lower(), args)
                last_name = translate_characters(employee_data['lastName'].lower(), args)
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

def authenticated_call(args,custom_email):
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
    username_field.send_keys(args.username)

    password_field = driver.find_element(By.ID, 'password')
    password_field.send_keys(args.password)

    # Submit the login form
    password_field.send_keys(Keys.RETURN)

    wait = WebDriverWait(driver, 10)
    try:
        # Wait for the login process to complete (adjust the timeout if needed)
        wait.until(EC.any_of(EC.url_contains('www.xing.com'),EC.title_is('XING'),EC.title_contains('MFA')))
    except:
        print(f">>> Login was not successful.")
        sys.exit(0)


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
            "id": args.company,
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
            print(f">>> {employee_count} employees have been found.")

            if args.amount is None or args.amount >= 3000:
                if employee_count >= 3000:
                    returnable_amount = 2999
                    print(f">>>XING allows only extracting up to 3000 datasets.")
                else:
                    returnable_amount = employee_count
            else:
                returnable_amount = 2999

            # One could sort between LAST_NAME and CONNECTION_DEGREE

            employee_data = {
                "operationName": "Employees",
                "variables": {
                    "consumer": "",
                    "includeTotalQuery":True,
                    "id": company_id,
                    "first": returnable_amount,
                    "query": {
                        "consumer": "web.entity_pages.employees_subpage",
                        "sort": args.sort
                    }
                },
                "query": "query Employees($id: SlugOrID!, $first: Int, $after: String, $query: CompanyEmployeesQueryInput!, $consumer: String! = \"\", $includeTotalQuery: Boolean = true) {\n  company(id: $id) {\n    id\n    totalEmployees: employees(first: 0, query: {consumer: $consumer}) @include(if: $includeTotalQuery) {\n      total\n      __typename\n    }\n    employees(first: $first, after: $after, query: $query) {\n      total\n      edges {\n       node {\n         contactDistance {\n            distance\n            __typename\n          }\n          sharedContacts {\n            total\n            __typename\n          } \n profileDetails {\n id\n            firstName\n     lastName\n          displayName\n            gender\n            pageName\n            profileImage(size: SQUARE_256) {\n              url\n              __typename\n            }\n    clickReasonProfileUrl(clickReasonId: CR_WEB_PUBLISHER_EMPLOYEES_MODULE) {\n              profileUrl\n              __typename\n            }\n            userFlags {\n              displayFlag\n              __typename\n            }\n            occupations {\n     headline\n          subline\n              __typename\n            }\n location { city \n street\n  zip \n __typename}\n            __typename\n          }  \n          networkRelationship {\n          id\n            relationship\n            permissions\n            error\n            __typename\n          } \n          __typename\n        }\n        __typename\n      }\n      pageInfo {\n        endCursor\n        hasNextPage\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}"
            }

            employee_response = requests.post(api_url, headers=headers, json=employee_data)

            # Check the response status code
            if employee_response.status_code == 200:
                return authenticated_employee_parsing(employee_response.json(), args, custom_email, api_url, headers)
            else:
                print(f">>> Employee request failed with status code {employee_response.status_code}")
                sys.exit(0)
        else:
            print(f">>> Employee count request failed with status code{employee_count_response.status_code}")
            sys.exit(0)
    else:
        print(f">>> Company request failed with status code {company_response.status_code}")
        sys.exit(0)

def authenticated_employee_parsing(employee_response, args, custom_email, api_url, headers):
    csv_data_list = []

    employees = employee_response['data']['company']['employees']['edges']

    if args.csv_header:
        csv_data_list.append([f"Email Address{args.csv_separator}Alternative Email Address{args.csv_separator}Display-Name{args.csv_separator}Firstname{args.csv_separator}Lastname{args.csv_separator}Gender{args.csv_separator}Occupations{args.csv_separator}Profile-URL{args.csv_separator}City{args.csv_separator}Street{args.csv_separator}ZIP{args.csv_separator}Mobile Number{args.csv_separator}Fax Number{args.csv_separator}Telephone number{args.csv_separator}"])

    potential_email_schemes = []
    potential_name_schemes = []
    employee_json_data = []
    # Extract and print employee information
    for edge in employees:
        node = edge['node']
        profile_details = node['profileDetails']
        if profile_details is not None:
        
            profile_url = profile_details['clickReasonProfileUrl']['profileUrl'] if profile_details['clickReasonProfileUrl'] is not None else ""
            
            first_name = translate_characters(profile_details['firstName'].lower(), args)
            last_name = translate_characters(profile_details['lastName'].lower(), args)
            display_name = profile_details['displayName']
            gender = profile_details['gender']

            city =  translate_characters(profile_details['location']['city'], args) if profile_details['location']['city'] is not None else ""
            street = translate_characters(profile_details['location']['street'], args) if profile_details['location']['street'] is not None else ""
            
            xing_email_address = ""
            mobile_number = ""
            fax_number = ""
            telephone_number = ""
            zip_code = ""

            if street:
                contact_data = {
                    "operationName":"profileContactDetails",
                    "variables": {
                        "profileId": profile_details['pageName']
                    },
                    "query":"query profileContactDetails($profileId: SlugOrID!) {\n  profileModules(id: $profileId) {\n    xingIdModule {\n      ...xingIdContactDetails\n      outdated\n      lastModified\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment xingIdContactDetails on XingIdModule {\n  contactDetails {\n    business {\n      address {\n        city\n        country {\n          countryCode\n          name: localizationValue\n          __typename\n        }\n        province {\n          id\n          canonicalName\n          name: localizationValue\n          __typename\n        }\n        street\n        zip\n        __typename\n      }\n      email\n      fax {\n        phoneNumber\n        __typename\n      }\n      mobile {\n        phoneNumber\n        __typename\n      }\n      phone {\n        phoneNumber\n        __typename\n      }\n      __typename\n    }\n    private {\n      address {\n        city\n        country {\n          countryCode\n          name: localizationValue\n          __typename\n        }\n        province {\n          id\n          canonicalName\n          name: localizationValue\n          __typename\n        }\n        street\n        zip\n        __typename\n      }\n      email\n      fax {\n        phoneNumber\n        __typename\n      }\n      mobile {\n        phoneNumber\n        __typename\n      }\n      phone {\n        phoneNumber\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}"
                }
                contact_data_response = requests.post(api_url, headers=headers, json=contact_data)

                if contact_data_response.status_code == 200:
                    contact_data_response = contact_data_response.json()
                    business_data = contact_data_response['data']['profileModules']['xingIdModule']['contactDetails']['business']
                    mobile_number = business_data['mobile']['phoneNumber'] if business_data['mobile'] is not None else ""
                    fax_number = business_data['fax']['phoneNumber'] if business_data['fax'] is not None else ""
                    telephone_number = business_data['phone']['phoneNumber'] if business_data['phone'] is not None else ""
                    zip_code = business_data['address']['zip'] if  business_data['address'] is not None else ""
                    if business_data['email'] is not None:
                        xing_email_address = business_data['email']
                        split_email = business_data['email'].split("@")
                        potential_email_schemes.append(split_email[1])
                        potential_name_schemes.append(f"{split_email[0]}@{split_email[1]}")
                else:
                    print(f">>> Contact data request failed with status code {contact_data_response.status_code}")
                    sys.exit(0)


            occupations_all = profile_details['occupations']
            occupations_list = [occupation['subline'] for occupation in occupations_all]
            occupations = '| '.join(occupations_list)

            csv_data = {
                "profile_url": profile_url,
                "first_name": first_name,
                "last_name": last_name,
                "display_name": display_name,
                "gender": gender,
                "occupations": occupations,
                "city": city,
                "street": street,
                "zip_code": zip_code,
                "mobile_number": mobile_number,
                "fax_number": fax_number,
                "telephone_number": telephone_number,
                "xing_email_address": xing_email_address
            }
            
            employee_json_data.append(csv_data)
   
    email_address = ""    
    company_domain = args.domain
    if custom_email is None:
        potential_email_schemes = list(set(potential_email_schemes))
        if len(potential_email_schemes) > 0:
            for index, scheme in enumerate(potential_email_schemes, start=1):
                print(f"{index}. {scheme}")
            
            if args.ignore:
                user_choice  = 0
            else:
                user_choice = input(">>> Potential email address schemes were discovered in the XING data. Do you wish to use any of them? If so, pick a number please or 0 to continue: ")
            try:
                user_choice = int(user_choice)
                if user_choice == 0:
                    print(f">>> Continuing with user-defined company domain >> {company_domain} <<")
                elif 1 <= user_choice <= len(potential_email_schemes):
                    company_domain = potential_email_schemes[user_choice - 1]
                    print(f">>> Continuing with company domain >> {company_domain} <<")
                else:
                    print(">>> Invalid choice. Please enter a valid number.")
            except ValueError:
                print(">>> Invalid input. Please enter a number.")

        for employee in employee_json_data:
            email_address = generate_email(employee['first_name'],employee['last_name'],company_domain,args.format)
            employee['email_address'] = email_address
    else:
        for employee in employee_json_data:
            email_address = generate_email(employee['first_name'],employee['last_name'],company_domain,1,custom_email)
            employee['email_address'] = email_address
        
    
    for employee in employee_json_data:
        csv_entry = [f"{employee['email_address']}{args.csv_separator}{employee['xing_email_address']}{args.csv_separator}{employee['display_name']}{args.csv_separator}{employee['first_name']}{args.csv_separator}{employee['last_name']}{args.csv_separator}{employee['gender']}{args.csv_separator}{employee['occupations']}{args.csv_separator}{employee['profile_url']}{args.csv_separator}{employee['city']}{args.csv_separator}{employee['street']}{args.csv_separator}{employee['zip_code']}{args.csv_separator}{employee['mobile_number']}{args.csv_separator}{employee['fax_number']}{args.csv_separator}{employee['telephone_number']}"]
        csv_data_list.append(csv_entry)

    return csv_data_list, employee_json_data


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
    parser.add_argument('-o','--output', type=str, default='employees', help='The name of the CSV file to save the output')
    parser.add_argument('--csv-separator', type=str, default=";", help='Desired CVS file separator, default: ";"')
    parser.add_argument("--csv-header", action="store_true", help="Include header in CSV file")
    parser.add_argument("--stdout", action="store_true", help="Print results to screen")
    parser.add_argument('--double-name-separator', type=str, default="-", help='Desired separator for double names, default: "-"')
    parser.add_argument('--ignore', action="store_true", help='Ignore interactive options')
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
        csv_data_list = unauthenticated_call(args.company, args.domain, args.format, custom_email, args.csv_separator, args.csv_header)
    else:
        csv_data_list, json_data_list = authenticated_call(args, custom_email)

    with open(output_file + ".csv", 'w') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data_list)
            print(f">>> CSV-formatted employee data saved to {output_file}.csv")

    with open(output_file + ".json", 'w') as json_file:
        json.dump(json_data_list, json_file, indent=2)
        print(f">>> JSON-formatted employee data saved to {output_file}.json")
    if args.stdout:
        print('\n'.join(''.join(map(str,entry)) for entry in csv_data_list))
