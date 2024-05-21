#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  TEMPLATE GROUPS IMPORT VIA CREATING

import argparse
import pprint
from pyzabbix import ZabbixAPI
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


ZABBIX_USER_5 = ''
ZABBIX_PASSWORD_5 = ''
ZABBIX_URL_5 = ''
ZABBIX_URL_7 = ''


def parse_args():
    """
    :return: arguments : namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', required=True, help='FINAMTRADE логин от заббикса', type=str)
    parser.add_argument('--password', required=True, help='FINAMTRADE пароль от заббикса', type=str)
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        username = args.user
        password = args.password
        zbxapi_5 = ZabbixAPI(ZABBIX_URL_5)
        zbxapi_5.login(ZABBIX_USER_5, ZABBIX_PASSWORD_5)

        zbxapi_7 = ZabbixAPI(ZABBIX_URL_7)
        zbxapi_7.session.verify = False
        zbxapi_7.login(username, password)

        groups_info = zbxapi_5.hostgroup.get(
            search={'name': 'Zabbix template'}
        )
        for group in groups_info:
            groups_info = zbxapi_7.hostgroup.create(
                name=group['name']
            )
    except:
        pass


if __name__ == "__main__":
    main()

