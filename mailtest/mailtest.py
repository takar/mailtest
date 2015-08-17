#!/usr/bin/env python
"""
Mailtest utility
"""

# General
import os
import sys
from os.path import expanduser
import argparse
import json
import logging

# Sending
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.utils import formatdate, make_msgid

# Receiving
import imaplib
from email import message_from_string

# Comparing
import time
import functools


def mail_compare(msg1, msg2):
    if msg1['Subject'] != msg2['Subject']:
        logging.debug('The subjects are different\n> {}\n> {}'.format(
            msg1['Subject'], msg2['Subject']))
        return False

    if msg1['Date'] != msg2['Date']:
        logging.debug('The dates are different\n> {}\n> {}'.format(
            msg1['Date'], msg2['Date']))
        return False

    logging.debug('Messages are the same')

    return True


def mailtest_send(config):
    msg = MIMEMultipart()
    msg['From'] = '"{from_name}" <{from_addr}>'.format(
        from_name=config['message']['from_name'],
        from_addr=config['message']['from_addr'])
    msg['To'] = '"{to_name}" <{to_addr}>'.format(
        to_name=config['message']['to_name'],
        to_addr=config['message']['to_addr'])
    msg['Subject'] = config['message']['subject']
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    msg.attach(MIMEText(config['message']['body'], 'plain'))

    if config['sending']['protocol'] == 'smtp':
        smtp = smtplib.SMTP
    elif config['sending']['protocol'] == 'smtps':
        smtp = smtplib.SMTP_SSL
    else:
        raise NotImplementedError()

    con = smtp(config['sending']['host'], config['sending']['port'])
    con.set_debuglevel(1)
    con.sendmail(
        from_addr=config['message']['from_addr'],
        to_addrs=config['message']['to_addr'],
        msg=msg.as_string())
    con.quit()

    return msg


def mailtest_receive(config, msg_send):
    if config['receiving']['protocol'] == 'imap':
        imap = imaplib.IMAP4
    elif config['receiving']['protocol'] == 'imaps':
        imap = imaplib.IMAP4_SSL
    else:
        raise NotImplementedError()

    con = imap(config['receiving']['host'], config['receiving']['port'])
    con.debug = 4
    con.login(config['receiving']['username'],
              config['receiving']['password'])
    con.select()
    typ, data = con.search(None, 'ALL')
    found = False
    for num in data[0].split():
        typ, data = con.fetch(num, '(RFC822)')
        msg_rcvd = message_from_string(data[0][1])
        found = found or mail_compare(msg_send, msg_rcvd)
        if found:
            con.store(num, '+FLAGS', '\\Deleted')
            con.expunge()
            break
    con.close()
    con.logout()

    return found


def retry_with_timeout(fn, retry, timeout):
    for i in range(0, retry):
        if fn():
            return True
        time.sleep(timeout)
    return False


def mailtest(config):
    msg = mailtest_send(config)
    fn = functools.partial(mailtest_receive, config, msg)
    return retry_with_timeout(fn, 6, 10)


def create_config(configfile):
    config = {
        'sending': {
            'host': 'localhost',
            'port': 25,
            'protocol': 'smtp',
            'username': '[username]',
            'password': '[password]',
        },
        'receiving': {
            'host': 'localhost',
            'port': 143,
            'protocol': 'imap',
            'username': '[username]',
            'password': '[password]'
        },
        'message': {
            'from_addr': '[sender@example.com]',
            'from_name': '[Sender Example]',
            'to_addr': '[receiver@example.com]',
            'to_name': '[Receiver Example]',
            'subject': 'Mailtest test message',
            'body': 'This test message is sent by mailtest.'
        }
    }
    contents = json.dumps(config, indent=4, separators=(',', ': '))

    with open(configfile, 'w') as fd:
        fd.write(contents)


def read_config(configfile):
    if not os.path.exists(configfile):
        create_config(configfile)

    with open(configfile) as fd:
        contents = fd.read()

    return json.loads(contents)


def parse_args():
    """ Parse the command line arguments """
    parser = argparse.ArgumentParser(description=__doc__)
    homedir = expanduser('~')
    configfile = os.path.join(homedir, '.mailtest')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-c', '--config', type=str, default=configfile)

    return parser.parse_args()


def main():
    args = parse_args()
    config = read_config(args.config)
    logging.StreamHandler(sys.stdout)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug('Setting log level to debug')
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug(config)
    if mailtest(config):
        exit(0)
    else:
        exit(1)


if __name__ == '__main__':
    """ Execute the main function """
    main()
