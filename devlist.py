import click
import requests
import json
import itertools
import re


def incrementer(start, iterable):
    for i in iterable:
        ret = (start, i)
        start+=1
        yield ret


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


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


info_choices = ['arplist', 'wlnoise', 'wldev', 'dhcpd_static', 'dhcpd_lease', 'all']
def get_info(content, info):
    def clean(seq):
        return filter(lambda x: x != '' and x != None, seq)

    (?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)
    (.*)=.?\[\s?(\[.*\])?\s?\];

    info_groups = clean(content.split(';'))
    info_groups = clean(k.strip().replace('\n','').replace('.split(\'>\')', '').replace('\'','').replace('[', '').replace('1>', '').replace('<', ',').replace(']', '').split('=') for k in info_groups)
    info_groups = { str(g[0]).strip():str(g[1]).strip() for g in info_groups }

    info_groups['arplist'] = json.dumps({
        "arplist":[
            {"interface":l, "mac":v, "ip":k} for k,v,l in grouper(3, info_groups['arplist'].split(','))
        ]
    })

    info_groups['wlnoise'] = json.dumps({ 
        "wlnoise":[ 
            {"eth{}".format(k):v} for k,v in incrementer(1, info_groups['wlnoise'].split(','))
        ]
    })

    info_groups['wldev'] = json.dumps({
        "wldev":[
            {"interface":a, "mac":b, "noise":c, "TX":d, "RX":e, "lease time":f} for a,b,c,d,e,f,g in grouper(7, info_groups['wldev'].split(','))
        ]
    })
    
    info_groups['dhcpd_static'] = json.dumps({
        'dhcpd_static':[
            {"mac":a, "ip":b, "hostname":c } for a,b,c in grouper(3, info_groups['dhcpd_static'][:-1].split(','))
        ]
    })

    info_groups['dhcpd_lease'] = json.dumps({
        'dhcpd_lease':[
            {"hostname":a, "ip":b, "mac":c, "lease":d+e} for a,b,c,d,e in grouper(5, info_groups['dhcpd_lease'].split(','))
        ]
    })    

    return json.dumps(info_groups) if info == 'all' else info_groups[info]


@click.command()
@click.argument('router_ip')
@click.argument('http_id')
@click.option('--user', default=None, type=str, help="The user for the request, default=None.")
@click.option('--password', default=None, type=str, help="The password for the request, default=None.")
@click.option('--info', type=click.Choice(info_choices), default='all', help='List of the available data, default=all.')
@click.option('--https', default=True, type=bool, help="Set the protocol to https, default=True.")
@click.option('--verify_ssl_certificate', default=True, type=bool, help="If the https option in enable this force the ssl certificate to be verified, default=True.")
def main(router_ip, http_id, https, verify_ssl_certificate, user, password, info):
    content, code = get_devlist(router_ip, http_id, https, verify_ssl_certificate, user, password)
    if code == 200:
        print(get_info(content, info))
    else:
        print('Server returned : {}'.format(code))


if __name__ == "__main__":
    main()