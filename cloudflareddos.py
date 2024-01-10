#!/usr/bin/python3

import argparse
import sys
import requests
import re
import json
import subprocess
import shlex
import CloudFlare


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# funcation for argument
def setArgument():
    parser = argparse.ArgumentParser(description="Add Domain and set DDoS Block Null Route")
    parser.add_argument('-d','--domain',help='Specify domain name',required=True)
    parser.add_argument('-fd','--filedns',help='Specify DNS Zone File',required=False)
   # parser.add_argument('-yd','--yaml-dns',help='Specify DNS Config in YAML')
    parser.add_argument('-l','--localhost',help='Set to Localhost',action='store_true')
    args = parser.parse_args()
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    return args
# used for zone requests as an alternative if python cloudflare wrapper is not working
def rawzonesrequest(zone_id,data,feature):
    url="https://api.cloudflare.com/client/v4/zones/{}/{}".format(zone_id,feature)
    
    with open('/home/devnull/.cloudflare/cloudflare.cfg','r') as f:
        lines=f.readlines()
        auth=()
        for l in lines:
            if match := re.findall("^token\s*=\s*(\S+)",l):
                auth+=tuple(match)
                break
            if match := re.findall("^email\s*=\s*(\S+)",l):
                auth+=tuple(match)
            elif match := re.findall("^key\s*=\s*(\w+)",l):
                auth+=tuple(match)
        #data={
        #'fight_mode': True
        #}
        headers={
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:73.0) Gecko/20100101 Firefox/73.0',
            'Authorization': 'Bearer '+auth[0],
            'Content-Type': 'application/json'
        }
        #r=requests.put(url=url,data=json.dumps(data),headers=headers)
        r=requests.put(url=url,data=json.dumps(data),headers=headers)
        return r.text

# if dns zone is not empty, delete all dns records
def deleteAllDNS(cf,zone_id):
    try:
        dns_records = cf.zones.dns_records.get(zone_id)

        if dns_records:
            for dns_record in dns_records:
                dns_record_id = dns_record['id']
                r = cf.zones.dns_records.delete(zone_id,dns_record_id)
                print(f"{bcolors.OKBLUE}Delete DNS Records{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit(f'{bcolors.FAIL}/zones.get: %d %s - api call failed{bcolors.ENDC}' %(e,e))

# function for set dns to localhost
def setLocalhost(cf,zone_id):
    dns_records = [
        {'name':'@','type':'A','content':'127.0.0.1'},
        {'name':'@','type':'AAAA','content':'::1'}
    ]
    deleteAllDNS(cf,zone_id)
    try:
        for dns_record in dns_records:
            r = cf.zones.dns_records.post(zone_id,data=dns_record)
            print(f"{bcolors.OKBLUE} Add Record DNS{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('zones.post: %d %s - api call failed' % (e, e))

# function for importing dns zones
def importDNSZones(cf,zone_id,fd ):
    try:
        deleteAllDNS(cf,zone_id)
        with open(fd,'r') as f:
            dns_records_import = getattr(cf.zones.dns_records,'import_')
            # post(identifier1=None, identifier2=None, identifier3=None, identifier4=None, params=None, data=None, files=None) method of CloudFlare.cloudflare._AddWithAuth instance
            # Cloudflare v4 API

            r = dns_records_import.post(zone_id,params={'proxied':'true'},files={'file':f})
            # proxied param not working
            # now is rate limited
            print(f"{bcolors.OKBLUE}Import DNS Zone{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
            return r
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('zones.post: %d %s - api call failed' % (e, e))

# function for deleting NS record line
def deleteLineNS(filedns):
    with open(filedns,'r+') as f:
        data = f.readlines()
        for linen,line in enumerate(data):
            linenew=re.sub(r'.*IN\s+NS\s+\S+','',line)
            if linenew:
                #print(linenew)
                data.pop(linen)
                data.insert(linen,linenew)
        f.truncate(0)
        f.seek(0)
        f.writelines(data)
    return filedns
# activated i'm under attack
def setUnderAttack(cf,zone_id):
    try:
        r = cf.zones.settings.security_level.patch(zone_id,data={"value": "under_attack"})
        print(f"{bcolors.OKBLUE}Activating Under Attack{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
        return r
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit(f'{bcolors.FAIL}under attack activation: %d %s - api call failed{bcolors.ENDC}' % (e, e))

# activated bot fight mode with rawzonesrequest as an alternative because python cloudflare wrapper not working well with put request at bot_management
def setBotFight(cf,zone_id):
    try:
        data = {
            'fight_mode': True
        }
        r=rawzonesrequest(zone_id,data,'bot_management')
        print(f"{bcolors.OKBLUE}Activating Bot Fight Mode{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
        return r
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit(f'{bcolors.FAIL}cloudflare: %d %s - api call failed{bcolors.ENDC}' % (e, e))


def setFirewallDoS(cf,domain,zone_id):
    typer=['A','AAAA']
    listout=tuple()
    for t in typer:
        cmd='dig @ns1.domainesia.net {} {} +short'.format(domain,t)
        
        proc=subprocess.Popen(shlex.split(cmd),stdout=subprocess.PIPE)
        out,err=proc.communicate()
        listout+=tuple([out.decode('utf-8').split('\n')[0]])
    try:
        #challenge_id: (ip.geoip.country eq "ID" and not ip.src in {ipserverhostingnya})
        #BlockDDOS: (ip.geoip.country ne "ID" and ip.geoip.country in {"CA" "CN" "IE" "NL" "RO" "RU" "TT" "GB" "US"} and not ip.geoip.asnum in {32934 394699 15169 22577} and not ip.src in {ipserverhostingnya})
        #only_id: (ip.geoip.country ne "ID" and not ip.geoip.asnum in {32934 394699 15169 22577} and not ip.src in {ipserverhostingnya})
        expressions={
            'challenge_id': '(ip.geoip.country eq \"ID\" and not ip.src in {%s %s})' %(listout[0],listout[1]),
            'BlockDDOS': '(ip.geoip.country ne \"ID\" and ip.geoip.country in {"CA" "CN" "IE" "NL" "RO" "RU" "TT" "GB" "US"} and not ip.geoip.asnum in {32934 394699 15169 22577} and not ip.src in { %s %s })' %(listout[0],listout[1]),
            'only_id': '(ip.geoip.country ne \"ID\" and not ip.geoip.asnum in {32934 394699 15169 22577} and not ip.src in { %s %s })' %(listout[0],listout[1])
        }
        for keys,value in expressions.items():
            if keys == "challenge_id":
                action="js_challenge"
            else:
                action="block"
            params = [{
                    "action": action,
                    "description": keys,
                    "filter": {
                        "expression": value,          
                        "paused": False,
                    }
                }]
            try:
                r = cf.zones.firewall.rules.post(zone_id,data=params)
                print(f"{bcolors.OKBLUE}Set Firewall Rules{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
            except CloudFlare.exceptions.CloudFlareAPIError as e:
                if int(e) == 10202:
                    print(f"{bcolors.WARNING}WAF Have Been Added Before{bcolors.ENDC}")

    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit(f'{bcolors.FAIL}cloudflare: %d %s - api call failed{bcolors.ENDC}' % (e, e))
def activatedL7DDoSHTTP(cf,zone_id):
    try:
        data= {
            "description": "Execute HTTP DDoS Attack Protection Managed Ruleset in the zone-level phase entry point ruleset",
            "rules": [
                {
                    "action": "execute",
                    "action_parameters": {
                        "overrides": {
                            "sensitivity_level": "high",
                            "action": "block",
                            "categories": [
                                {
                                    "sensitivity_level": "high"
                                    }
                                    ],
                                    "rules": [
                                        {
                                            "action": "block"
                                        }
                                    ]
                                    }
                                    },
                                    "expression": "true",
                                }
                            ]
                }
        print(json.dumps(data))
        r = cf.zones.rulesets.phases.ddos_l7.entrypoint.put(zone_id,data=data)
        print(f"{bcolors.OKBLUE}Set L7 DDoS HTTP{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(r))
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit(f'{bcolors.FAIL}cloudflare: %d %s - api call failed{bcolors.ENDC}' % (e, e))

def main():
    args=setArgument()
    domain=args.domain

    cf = CloudFlare.CloudFlare(profile="work")
    try:
        zone_info = cf.zones.post(data={'jump_start':False,'name':domain})
        print(f"{bcolors.OKBLUE}Nameservers:{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(" ".join(zone_info['name_servers'])))
        zone_id = zone_info['id']
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        if int(e)==1061:
            zone_info = cf.zones.get(params={'name': domain})
            print(f"{bcolors.OKBLUE}Nameservers:{bcolors.ENDC}: {bcolors.OKGREEN}%s{bcolors.ENDC}" %(" ".join(zone_info[0]['name_servers'])))
            zone_id = zone_info[0]['id']
        else:
            exit('cloudflare: %d %s - api call failed' % (e, e))
    except Exception as e:
        exit(f'{bcolors.FAIL}cloudflare: %s - api call failed{bcolors.ENDC}' % (e))
    # print(zone_info)
    if zone_id:
    # print(args.filedns)
    # print(domain)
        if args.filedns is None:
            ### set dns to localhost ###
            # print(args.localhost)
            if args.localhost==True:
                setLocalhost(cf,zone_id)
        else:
            ### delete NS record line at dns zone db and import dns zone db to cloudflare
            filedns=args.filedns
            filedns=deleteLineNS(filedns)
            importDNSZones(cf,zone_id,filedns)
    
        ### set under attack mode ###
        setUnderAttack(cf,zone_id)
        ## set bot fight mode ###
        setBotFight(cf,zone_id)
        ### set firewall DoS ###
        setFirewallDoS(cf,domain,zone_id)

        # activatedL7DDoSHTTP(cf,zone_id)
    else:
        print(f"{bcolors.FAIL}Zone ID is not Defined!{bcolors.ENDC}")
    
if __name__ == '__main__':
    main()

