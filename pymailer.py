#!/usr/bin/env python

import csv
from datetime import datetime
from email import message
import logging
import os
import re
import smtplib
import sys
from time import sleep

import config

# Setup logging to specified log file
logging.basicConfig(filename=config.LOG_FILENAME, level=logging.DEBUG)


class PyMailer():
    """
    A python bulk mailer commandline utility. Takes five arguments: the path to the html file to be parsed; the
    database of recipients (.csv); the subject of the email; email adsress the mail comes from; and the name the email
    is from.
    """
    def __init__(self, html_path, csv_path, subject, *args, **kwargs):
        self.html_path = html_path
        self.csv_path = csv_path
        self.subject = subject
        self.from_name = kwargs.get('from_name', config.SES_FROM_NAME)
        self.from_email = kwargs.get('to_name', config.SES_FROM_EMAIL)

    def _stats(self, message):
        """
        Update stats log with: last recipient (incase the server crashes); datetime started; datetime ended; total
        number of recipients attempted; number of failed recipients; and database used.
        """
        try:
            stats_file = open(config.STATS_FILE, 'r')
        except IOError:
            raise IOError("Invalid or missing stats file path.")

        stats_entries = stats_file.read().split('\n')

        # Check if the stats entry exists if it does overwrite it with the new message
        is_existing_entry = False
        if stats_entries:
            for i, entry in enumerate(stats_entries):
                if entry:
                    if message[:5] == entry[:5]:
                        stats_entries[i] = message
                        is_existing_entry = True

        # If the entry does not exist append it to the file
        if not is_existing_entry:
            stats_entries.append(message)

        stats_file = open(config.STATS_FILE, 'w')
        for entry in stats_entries:
            if entry:
                stats_file.write("%s\n" % entry)
        stats_file.close()

    def _validate_email(self, email_address):
        """
        Validate the supplied email address.
        """
        if not email_address or len(email_address) < 5:
            return None
        if not re.match(r'^[a-zA-Z0-9._%-+]+@[a-zA-Z0-9._%-]+.[a-zA-Z]{2,6}$', email_address):
            return None
        return email_address

    def _retry_handler(self, recipient_data):
        """
        Write failed recipient_data to csv file to be retried again later.
        """
        try:
            # Open the file in text mode with append (`a`) to add retries without overwriting
            with open(config.CSV_RETRY_FILENAME, 'a', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow([
                    recipient_data.get('name', ''),  # Default to an empty string if 'name' is None
                    recipient_data.get('email', '')  # Default to an empty string if 'email' is None
                ])
        except IOError:
            raise IOError("Invalid or missing CSV file path.")

    # def _html_parser(self, recipient_data):
    #     """
    #     Open, parse and substitute placeholders with recipient data.
    #     """
    #     try:
    #         html_file = open(self.html_path, 'rb')
    #     except IOError:
    #         raise IOError("Invalid or missing html file path.")
    #
    #     html_content = html_file.read()
    #     if not html_content:
    #         raise Exception("The html file is empty.")
    #
    #     # Replace all placeolders associated to recipient_data keys
    #     if recipient_data:
    #         for key, value in recipient_data.items():
    #             placeholder = "<!--%s-->" % key
    #             html_content = html_content.replace(placeholder, value)
    #
    #     return html_content

    def _html_parser(self, recipient_data):
        """
        Open, parse, and substitute placeholders with recipient data and config variables.
        """
        try:
            with open(self.html_path, 'rb') as html_file:
                html_content = html_file.read().decode('utf-8')  # Decode binary content to string
        except IOError:
            raise IOError("Invalid or missing HTML file path.")

        if not html_content:
            raise Exception("The HTML file is empty.")

        # Replace all placeholders associated with recipient_data keys
        if recipient_data:
            for key, value in recipient_data.items():
                placeholder = f"{{{{{key}}}}}"  # Template placeholder format: {{key}}
                html_content = html_content.replace(placeholder, value or '')

        # Replace placeholders with config variables
        for key, value in vars(config).items():
            if not key.startswith("__"):  # Skip special/magic variables
                placeholder = f"{{{{{key}}}}}"  # Template placeholder format: {{key}}
                html_content = html_content.replace(placeholder, str(value) or '')

        return html_content

    def _form_email(self, recipient_data):
        """
        Form the html email, including mimetype and headers.
        """

        # Form the recipient and sender headers
        recipient = "%s <%s>" % (recipient_data.get('name'), recipient_data.get('email'))
        sender = "%s <%s>" % (self.from_name, self.from_email)

        # Get the html content
        html_content = self._html_parser(recipient_data)

        # Instatiate the email object and assign headers
        email_message = message.Message()
        email_message.add_header('From', sender)
        email_message.add_header('To', recipient)
        email_message.add_header('Subject', self.subject)
        email_message.add_header('MIME-Version', '1.0')
        email_message.add_header('Content-Type', 'text/html')
        email_message.set_payload(html_content)

        return email_message.as_string()

    def _parse_csv(self, csv_path=None):
        """
        Parse the entire csv file and return a list of dicts.
        """
        if not csv_path:
            csv_path = self.csv_path

        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as csv_file:
                csv_reader = csv.reader(csv_file)
                recipient_data_list = []
                for i, row in enumerate(csv_reader):
                    try:
                        recipient_name = row[0].strip() if row[0] else ''
                        recipient_email = self._validate_email(row[1].strip()) if len(row) > 1 else None
                    except IndexError:
                        recipient_name = ''
                        recipient_email = None

                    if not recipient_email:
                        logging.error(f"Invalid or missing email in line {i + 1}: {row}")
                        continue

                    recipient_data_list.append({
                        'name': recipient_name,
                        'email': recipient_email,
                    })

                return recipient_data_list
        except IOError:
            raise IOError("Invalid or missing CSV file path.")

    # def send(self, retry_count=0, recipient_list=None):
    #     """
    #     Iterate over the recipient list and send the specified email.
    #     """
    #     if not recipient_list:
    #         recipient_list = self._parse_csv()
    #         if retry_count:
    #             recipient_list = self._parse_csv(config.CSV_RETRY_FILENAME)
    #
    #     # Save the number of recipient and time started to the stats file
    #     if not retry_count:
    #         self._stats("TOTAL RECIPIENTS: %s" % len(recipient_list))
    #         self._stats("START TIME: %s" % datetime.now())
    #
    #     # Instantiate the number of falied recipients
    #     failed_recipients = 0
    #
    #     for recipient_data in recipient_list:
    #         # Instantiate the required vars to send email
    #         message = self._form_email(recipient_data)
    #         if recipient_data.get('name'):
    #             recipient = "%s <%s>" % (recipient_data.get('name'), recipient_data.get('email'))
    #         else:
    #             recipient = recipient_data.get('email')
    #         sender = "%s <%s>" % (self.from_name, self.from_email)
    #
    #         # Send the actual email
    #         smtp_server = smtplib.SMTP(host=config.SMTP_HOST, port=config.SMTP_PORT)
    #         try:
    #             smtp_server.sendmail(sender, recipient, message)
    #
    #             # Save the last recipient to the stats file incase the process fails
    #             self._stats("LAST RECIPIENT: %s" % recipient)
    #
    #             # Allow the system to sleep for .25 secs to take load off the SMTP server
    #             sleep(0.25)
    #         except:
    #             logging.error("Recipient email address failed: %s" % recipient)
    #             self._retry_handler(recipient_data)
    #
    #             # Save the number of failed recipients to the stats file
    #             failed_recipients = failed_recipients + 1
    #             self._stats("FAILED RECIPIENTS: %s" % failed_recipients)

    def send(self, retry_count=0, recipient_list=None, use_ses=False):
        """
        Iterate over the recipient list and send the specified email.
        """
        if not recipient_list:
            recipient_list = self._parse_csv()
            if retry_count:
                recipient_list = self._parse_csv(config.CSV_RETRY_FILENAME)

        # Choose SMTP settings and override sender details if using SES
        if use_ses:
            smtp_host = config.SES_SMTP_HOST
            smtp_port = config.SES_SMTP_PORT
            from_name = config.SES_FROM_NAME or self.from_name  # Override from_name
            from_email = config.SES_FROM_EMAIL or self.from_email  # Override from_email
            email_password = config.SES_EMAIL_PASSWORD
            account_id = config.SES_ACCOUNT_ID  # Use account ID as username for SES
        else:
            smtp_host = config.SMTP_HOST
            smtp_port = config.SMTP_PORT
            from_name = self.from_name  # Use default from_name
            from_email = self.from_email  # Use default from_email
            email_password = config.EMAIL_PASSWORD
            account_id = config.ACCOUNT_ID  # Default username for regular SMTP

        # Save the number of recipients and time started
        total_recipients = len(recipient_list)
        self._stats(f"TOTAL RECIPIENTS: {total_recipients}")
        self._stats(f"START TIME: {datetime.now()}")

        failed_recipients = 0
        successful_recipients = 0

        # Open SMTP connection
        try:
            smtp_server = smtplib.SMTP(host=smtp_host, port=smtp_port)
            smtp_server.starttls()
            if email_password:
                smtp_server.login(account_id, email_password)

            for i, recipient_data in enumerate(recipient_list, start=1):
                message = self._form_email(recipient_data)
                sender = f"{from_name} <{from_email}>"
                recipient = f"{recipient_data.get('name')} <{recipient_data.get('email')}>" if recipient_data.get(
                    'name') else recipient_data.get('email')

                try:
                    smtp_server.sendmail(sender, recipient, message)
                    logging.info(f"Email successfully sent to: {recipient}")
                    successful_recipients += 1
                    print(f"[{i}/{total_recipients}] Successfully sent to: {recipient}")
                    self._stats(f"LAST RECIPIENT: {recipient}")
                except Exception as e:
                    logging.error(f"Failed to send email to {recipient}: {e}")
                    print(f"[{i}/{total_recipients}] Failed to send to: {recipient}. Error: {e}")
                    self._retry_handler(recipient_data)
                    failed_recipients += 1

            smtp_server.quit()

        except Exception as e:
            logging.error(f"SMTP connection failed: {e}")
            print(f"SMTP")

    def send_test(self, use_ses=False):
        """
        Send test emails to the recipients specified in the config.
        """
        self.send(recipient_list=config.TEST_RECIPIENTS, use_ses=use_ses)

    def resend_failed(self):
        """
        Try and resend to failed recipients two more times.
        """
        for i in range(1, 3):
            self.send(retry_count=i)

    def count_recipients(self, csv_path=None):
        return len(self._parse_csv(csv_path))
def main(sys_args):
    if not os.path.exists(config.CSV_RETRY_FILENAME):
        open(config.CSV_RETRY_FILENAME, 'wb').close()

    if not os.path.exists(config.STATS_FILE):
        open(config.STATS_FILE, 'wb').close()

    try:
        action, html_path, csv_path, subject, *extra_args = sys_args
        use_ses = '--use-ses' in extra_args
    except ValueError:
        print(
            "Not enough arguments supplied. PyMailer requests 1 option and 3 arguments: ./pymailer -s html_path csv_path subject [--use-ses]")
        sys.exit()

    # Validate the HTML path
    if not os.path.isfile(html_path):
        print(f"The file '{html_path}' does not exist. Please provide a valid path.")
        sys.exit()
    if not html_path.lower().endswith('.html'):
        print(f"The file '{html_path}' does not have a valid .html extension.")
        sys.exit()

    # Validate the CSV path
    if not os.path.isfile(csv_path):
        print(f"The file '{csv_path}' does not exist. Please provide a valid path.")
        sys.exit()
    if not csv_path.lower().endswith('.csv'):
        print(f"The file '{csv_path}' does not have a valid .csv extension.")
        sys.exit()

    print(f"Validated paths:\nHTML Path: {html_path}\nCSV Path: {csv_path}")

    pymailer = PyMailer(html_path, csv_path, subject)

    if action == '-s':
        confirmation = input(
            "You are about to send to {} recipients. Do you want to continue (yes/no)? ".format(
                pymailer.count_recipients())
        )
        if confirmation.lower() in ['yes', 'y']:
            pymailer._stats("CSV USED: %s" % csv_path)
            pymailer.send(use_ses=use_ses)
            pymailer.resend_failed()
        else:
            print("Aborted.")
            sys.exit()

    elif action == '-t':
        confirmation = input(
            "You are about to send a test mail to all recipients as specified in config.py. Do you want to continue (yes/no)? "
        )
        if confirmation.lower() in ['yes', 'y']:
            pymailer.send_test(use_ses=use_ses)
        else:
            print("Aborted.")
            sys.exit()

    else:
        print(
            f"{action} option is not supported. Use either [-s] to send to all recipients or [-t] to send to test recipients")

    pymailer._stats("END TIME: %s" % datetime.now())

# def main(sys_args):
#     if not os.path.exists(config.CSV_RETRY_FILENAME):
#         open(config.CSV_RETRY_FILENAME, 'wb').close()
#
#     if not os.path.exists(config.STATS_FILE):
#         open(config.STATS_FILE, 'wb').close()
#
#     try:
#         action, html_path, csv_path, subject = sys_args
#     except ValueError:
#         print("Not enough argumants supplied. PyMailer requests 1 option and 3 arguments: ./pymailer -s html_path csv_path subject")
#         sys.exit()
#
#     if os.path.splitext(html_path)[1] != '.html':
#         print("The html_path argument doesn't seem to contain a valid html file.")
#         sys.exit()
#
#     if os.path.splitext(csv_path)[1] != '.csv':
#         print("The csv_path argument doesn't seem to contain a valid csv file.")
#         sys.exit()
#
#     pymailer = PyMailer(html_path, csv_path, subject)
#
#     if action == '-s':
#         confirmation = input(
#             "You are about to send to {} recipients. Do you want to continue (yes/no)? ".format(pymailer.count_recipients())
#         )
#         if confirmation in ['yes', 'y']:
#
#             # Save the csv file used to the stats file
#             pymailer._stats("CSV USED: %s" % csv_path)
#
#             # Send the email and try resend to failed recipients
#             pymailer.send()
#             pymailer.resend_failed()
#         else:
#             print("Aborted.")
#             sys.exit()
#
#     elif action == '-t':
#         confirmation = input(
#             "You are about to send a test mail to all recipients as specified in config.py. Do you want to continue (yes/no)? "
#         )
#         if confirmation in ['yes', 'y']:
#             pymailer.send_test()
#         else:
#             print("Aborted.")
#             sys.exit()
#
#     else:
#         print("{} option is not support. Use either [-s] to send to all recipients or [-t] to send to test recipients".format(action))
#
#     # Save the end time to the stats file
#     pymailer._stats("END TIME: %s" % datetime.now())

if __name__ == '__main__':
    main(sys.argv[1:])
