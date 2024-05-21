#### Zabbix upgrade 5.0 => 7.0: transfer templates and hosts to a new instance
- requires `pyzabbix` python module
- requires connection and administrator access to both instances
##### 1. import_template_groups_via_creating.py
creating groups with a name matching the regular expression from Zabbix 5 via  **hostgroup.create**

##### 2. import_zabbix_template_from_5_to_7.py
....

