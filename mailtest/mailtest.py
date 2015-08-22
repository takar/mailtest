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
import collections

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
        logging.debug('The subjects are different\n> {0}\n> {1}'.format(
            msg1['Subject'], msg2['Subject']))
        return False

    if msg1['Date'] != msg2['Date']:
        logging.debug('The dates are different\n> {0}\n> {1}'.format(
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

    cfg = config['sending']
    if cfg['protocol'] == 'smtp':
        smtp = smtplib.SMTP
        port = cfg['port'] if cfg['port'] else smtplib.SMTP_PORT
    elif cfg['protocol'] == 'smtps':
        smtp = smtplib.SMTP_SSL
        port = cfg['port'] if cfg['port'] else smtplib.SMTP_SSL_PORT
    elif cfg['protocol'] == 'starttls':
        smtp = smtplib.SMTP
        port = cfg['port'] if cfg['port'] else 587
    else:
        raise NotImplementedError()

    con = smtp(cfg['host'], port)
    con.set_debuglevel(1)
    if cfg['protocol'] == 'starttls':
        con.ehlo()
        con.starttls()
        con.ehlo()
    con.login(cfg['username'], cfg['password'])
    con.sendmail(
        from_addr=config['message']['from_addr'],
        to_addrs=config['message']['to_addr'],
        msg=msg.as_string())
    con.quit()

    return msg


def mailtest_receive(config, msg_send):
    cfg = config['receiving']
    if cfg['protocol'] == 'imap':
        imap = imaplib.IMAP4
        port = cfg['port'] if cfg['port'] else imaplib.IMAP4_PORT
    elif cfg['protocol'] == 'imaps':
        imap = imaplib.IMAP4_SSL
        port = cfg['port'] if cfg['port'] else imaplib.IMAP4_SSL_PORT
    else:
        raise NotImplementedError()

    con = imap(cfg['host'], port)
    con.debug = 4
    con.login(cfg['username'], cfg['password'])
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


def get_default_config():
    return {
        'sending': {
            'host': 'localhost',
            'port': None,
            'protocol': 'smtp',
            'username': '[username]',
            'password': '[password]'
        },
        'receiving': {
            'host': 'localhost',
            'port': None,
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


def merge_recursive(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = merge_recursive(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def read_config(configfile):
    default = get_default_config()

    if os.path.exists(configfile):
        with open(configfile) as fd:
            contents = fd.read()
    else:
        contents = json.dumps(default, indent=4, separators=(',', ': '))
        with open(configfile, 'w') as fd:
            fd.write(contents)

    return merge_recursive(default, json.loads(contents))


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
