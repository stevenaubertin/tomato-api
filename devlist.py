import click
import requests
import json
import itertools
import re


info_choices = ['arplist', 'wlnoise', 'wldev', 'dhcpd_static', 'dhcpd_lease']
ip_pattern = "((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))"
mac_pattern = "(([0-9A-F]{2}[:-]){5}([0-9A-F]{2}))"
interface_pattern = "(\w+\d?)"
number_pattern = "\s?(-?\d+)\s?"
hostname_pattern = "(\w+)"


def skip(iterable, count=1):
        current = 0
        for i in iterable:
            if current < count:
                current += 1
                continue
            yield i


def parse(pattern, content, flags=re.I | re.M):
    return re.findall(pattern, content, flags=flags)


def parse_arplist(content):
    matches = parse(r"\['{}','{}','{}'\]".format(ip_pattern, mac_pattern, interface_pattern), content)
    return json.dumps({
        "arplist": [ 
            {
                "ipv4":ip,
                "mac":mac,
                "interface":interface
            }
            for ip,mac,_,__,interface in matches 
        ]
    })


def parse_wlnoise(content):
    matches = parse(r"wlnoise = \[({0},{0})+\];".format(number_pattern), content)
    return json.dumps({
        "wlnoise":[
            m for m in skip(list(matches[0]))
        ]
    })


def parse_static(content):
    matches = parse(r"{}<{}<{}".format(mac_pattern, ip_pattern, hostname_pattern), content)
    return json.dumps({
        "dhcpd_static":[
            {
                "mac":mac,
                "ipv4":ip,
                "hostname":hostname
            }
            for mac, _, __, ip, hostname in matches
        ]
    })


def parse_wldev(content):
    matches = parse(r"\['{0}','{1}',{2},{2},{2},{2},{2}".format(interface_pattern, mac_pattern, number_pattern), content)
    return json.dumps({
        "wldev":[
            {
                "interface":interface,
                "mac":mac,
                "noise":noise,
                "tx":tx,
                "rx":rx,
                "lease":lease
            }
            for interface, mac, _, __, noise, tx, rx, lease, l in list(matches)
        ]
    })


def parse_lease(content):
    matches = parse(r"'{}','{}','{}','(\d?\s?\w*,\s?\d?\d?:\d?\d?:\d?\d?)".format(hostname_pattern, ip_pattern, mac_pattern), content)
    return json.dumps({
        "dhcpd_lease":[
            {
                "hostname":hostname,
                "interface":interface,
                "mac":mac,
                "lease":lease
            }
            for hostname, interface, mac, _, __, lease in matches
        ]
    })


def get_devlist(router_ip, http_id, https, verify_ssl_certificate, user, password):
    params = {
        "_http_id":http_id,
        "_nextwait":"1",
        "exec":"devlist"
    }
    response = requests.get(
        ''.join([ 'https://' if https else 'http://', router_ip, '/update.cgi']),
        auth=(user, password),
        headers={ 'cache-control': "no-cache" },
        params=params,
        verify=verify_ssl_certificate and https
    )
    return (response.text if response.status_code == 200 else None, response.status_code)


def get_info(content, info):
    if info == 'arplist':
        return parse_arplist(content)
    elif info == 'wlnoise':
        return parse_wlnoise(content)
    elif info == 'wldev':
        return parse_wldev(content)
    elif info == 'dhcpd_static':
        return parse_static(content)
    elif info == 'dhcpd_lease':
        return parse_lease(content)


@click.command()
@click.argument('router_ip')
@click.argument('http_id')
@click.option('--https', default=True, type=bool, help="Set the protocol to https, default=True")
@click.option('--verify_ssl_certificate', default=True, type=bool, help="If the https option in enable this force the ssl certificate to be verified, default=True")
@click.option('--user', default=None, type=str, help="default=None")
@click.option('--password', default=None, type=str, help="default=None")
@click.option('--info', type=click.Choice(info_choices), default='wldev')
def main(router_ip, http_id, https, verify_ssl_certificate, user, password, info):
    content, code = get_devlist(router_ip, http_id, https, verify_ssl_certificate, user, password)
    if code == 200:
        print(get_info(content, info))
    else:
        print('Server returned : {}'.format(code))


if __name__ == "__main__":
    main()