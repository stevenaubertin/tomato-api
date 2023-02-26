#!/bin/python

from logging import error
import requests
from requests.auth import HTTPBasicAuth
import re
import json
import sys
import urllib3

name_regex_str = r"[a-zA-Z0-9]*-?[a-zA-Z0-9]+"
ipv4_regex_str = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
ipv6_regex_str = r"[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}"

lease_regex = re.compile(
    "\[('{}','{}','{}')".format(name_regex_str, ipv4_regex_str, ipv6_regex_str), 
    re.IGNORECASE | re.MULTILINE
)
arplist_regex = re.compile(
    "'{}','{}','{}'".format(ipv4_regex_str, ipv6_regex_str, name_regex_str),
    re.IGNORECASE | re.MULTILINE
)
statics_regex = re.compile(
    "{}<{}<{}".format(ipv6_regex_str, ipv4_regex_str, name_regex_str),
    re.IGNORECASE | re.MULTILINE
)


def get_devices(username, password) -> str:
    urllib3.disable_warnings()
    basic = HTTPBasicAuth(username, password)
    response = requests.get('https://192.168.1.1/status-devices.asp?_=1659816271622', auth=basic, verify=False)

    devlist = response.text
    lease = [str(i).replace("'", '').split(',') for i in lease_regex.findall(devlist)]
    statics = [str(i).replace("'", '').split('<') for i in statics_regex.findall(devlist)]
    arplist = [str(i).replace("'", '').split(',') for i in arplist_regex.findall(devlist)]

    # Format lease
    l = [
        {
            'name': i[0],
            'mac': i[1] if ':' in i[1] else i[2],
            'ip': i[1] if ':' in i[2] else i[2],
        } for i in lease
    ]

    # Format statics
    s = [
        {
            'name': i[-1],
            'mac': i[0] if ':' in i[0] else i[1],
            'ip': i[0] if ':' in i[1] else i[1],
        } for i in statics
    ]

    # Format arplist
    def find_name(mac) -> str:
        r = [i for i in filter(lambda x: x['mac'] == mac, s + l)]
        return r[0]['name'] if len(r) > 0 else ''

    arp = {}
    for d in [{i[-1]:{j for j in i[:-1]}} for i in arplist]:
        k = [*d][0] # stupid python way of getting first keys
        values = [i for i in d[k]]
        mac = values[0] if ':' in values[0] else values[1]
        ip = values[1] if ':' in values[0] else values[0]
        name = find_name(mac)
        v = {
            'name': name,
            'mac': mac,
            'ip': ip
        }
        if k in arp.keys():
            arp[k].append(v)
        else:
            arp[k] = [v]

    return json.dumps({
        'arplist': arp,
        'lease': l,
        'statics': s
    })


def main(argv):
    if len(argv) == 0 :
        error('username and password are required, \nUSAGE :\n python '+__file__.split('\\')[-1]+' <username> <password>')
        sys.exit(-1)

    username = argv[0]
    password = argv[1]

    devices = get_devices(username, password)
    print(devices)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
