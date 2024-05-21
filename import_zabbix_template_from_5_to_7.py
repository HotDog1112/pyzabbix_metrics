#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import requests
from pyzabbix import ZabbixAPI
import urllib3
import xml.etree.ElementTree as ET
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# read-write access required
ZABBIX_USER_5 = ''
ZABBIX_PASSWORD_5 = ''
ZABBIX_URL_5 = ''
ZABBIX_URL_7 = ''
BB_USER = ""
BB_PASS = ""
BB_TEMPLATES = ""


def parse_and_create_template_groups(template_groups, zbxapi_5, zbxapi_7):
    """
    template_groups: array, zabbix 5 template groups
    zbxapi_5: object, ZabbixAPI 5.0 (old)
    zbxapi_7: object, ZabbixAPI 7.0 (new)
    """
    try:
        # если у шаблона более одной группы, и групп нет в Zabbix 7, создаем через templategroup.create
        for index, val in enumerate(template_groups):
            groupname = zbxapi_5.hostgroup.get(
                groupids=[int(val)],
                selectHostGroups='extend',
                output=['name'],
            )
            template_groups[index] = groupname[0]['name']

        for template_group in template_groups:
            if not zbxapi_7.templategroup.get(search={'name': template_group}):
                zbxapi_7.templategroup.create(name=template_group)
    except Exception as e:
        return e

    return ''


def parse_args():
    """
    :return: arguments : namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--user', default='', help='логин от Zabbix 7', type=str)
    parser.add_argument('--password', default='', help='пароль от Zabbix 7', type=str)
    return parser.parse_args()


def find_parent(element, tree):
    for parent in tree.iter():
        if element in parent:
            return parent
    return None


def main():
    template_id = 1 # id шаблона в Zabbix 5

    args = parse_args()
    username = args.user
    password = args.password

    # авторизация в Zabbix 5 и Zabbix 7
    zbxapi_5 = ZabbixAPI(ZABBIX_URL_5)
    zbxapi_5.login(ZABBIX_USER_5, ZABBIX_PASSWORD_5)

    zbxapi_7 = ZabbixAPI(ZABBIX_URL_7)
    zbxapi_7.session.verify = False
    zbxapi_7.login(username, password)

    # создаем сессию в BitBucket
    bb_session = requests.Session()
    bb_session.auth = (BB_USER, BB_PASS)

    template_info = zbxapi_5.template.get(
        templateids=[template_id],
        output='extend',
        selectTemplates='1',
        selectParentTemplates='1',
        selectGroups='1'
    )

    # парсим вывод
    template_name = template_info[0]['name']
    template_groups = [i['groupid'] for i in template_info[0]['groups']]

    # создаем нужные группы для шаблона
    get_create_t_groups = parse_and_create_template_groups(template_groups, zbxapi_5, zbxapi_7)


    # если группы создались
    if not get_create_t_groups:

        # создаем лог шаблонов  и триггеров, у которых есть зависимости
        logging.basicConfig(
            level=logging.INFO,
            filename="template_dependencies.log",
            filemode="w",
            format="%(asctime)s %(message)s \n"
        )

        response = bb_session.get(f'{BB_TEMPLATES}/browse/{template_name}.xml?limit=100000').json()
        xml_content = ''.join(line['text'] for line in response['lines'])

        # ищем зависимости триггеров, удаляем "инородные"
        tree = ET.fromstring(xml_content)

        all_trigger_dep = []
        for elem in tree.findall('.//trigger'):
            trigger_name = elem.find('name').text
            dep = elem.find('dependencies')
            if dep:
                values = dep.findall('dependency')
                for v in values:
                    name = v.find('name').text if v.find('name') is not None else None
                    expression = v.find('expression').text if v.find('expression') is not None else None
                    if expression:
                        dependent_template = expression.split(':')[0].replace('{', '')
                    if not re.search(f'{template_name}:', expression):
                        all_trigger_dep.append(f'\nШаблон: {template_name}\n'
                                               f'Триггер:{trigger_name}\n'
                                               f'Зависимость от: {dependent_template}, выражение триггерa: {expression}\n')
                elem.remove(dep)
        logging.info(''.join(all_trigger_dep))

        # если зависимости только внутри шаблона, можно импортировать
        is_ready = 1
        for depency in all_trigger_dep:
            if not re.search(template_name, depency):
                is_ready = 0

        if is_ready:
            # заменяем request_type, fix error -- Invalid parameter "/1/request_method": value must be 0
            for request_method in tree.findall('.//request_method'):
                parent = find_parent(request_method, tree)
                if parent is not None:
                    parent.remove(request_method)

            template = ET.tostring(tree, encoding='unicode')

            zbxapi_7.confimport(
                'xml',
                template,
                {
                    "discoveryRules": {"createMissing": True, "updateExisting": True},
                    "graphs": {"createMissing": True, "updateExisting": True},
                    "template_groups": {"createMissing": True, "updateExisting": True},
                    "hosts": {"createMissing": True, "updateExisting": True},
                    "images": {"createMissing": True, "updateExisting": True},
                    "items": {"createMissing": True, "updateExisting": True},
                    "maps": {"createMissing": True, "updateExisting": True},
                    # "screens": {"createMissing": True, "updateExisting": True},
                    "templates": {"createMissing": True, "updateExisting": True},
                    # "templateDashboards": {"createMissing": True, "updateExisting": True},
                    "triggers": {"createMissing": True, "updateExisting": True, 'deleteMissing': True},
                    "valueMaps": {"createMissing": True, "updateExisting": True},
                }
            )


if __name__ == "__main__":
    main()

