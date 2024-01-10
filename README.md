# Cloudflareddos
Python Script Used for Adding Domain to Cloudflare and Set Simple Firewall

### Requirement
- python-cloudflare from https://github.com/cloudflare/python-cloudflare, it can be installed with `pip install cloudflare`

### How to run

```
usage: cloudflareddos.py [-h] -d DOMAIN [-fd FILEDNS] [-l]

Add Domain and set DDoS Block Null Route

options:
  -h, --help            show this help message and exit
  -d DOMAIN, --domain DOMAIN
                        Specify domain name
  -fd FILEDNS, --filedns FILEDNS
                        Specify DNS Zone File
  -l, --localhost       Set to Localhost
```

#### Required Argument
-d DOMAIN or --domain DOMAIN : This is used for specifying domain name that will be added to cloudflare.

This will only add domain to cloudflare without any setup.


#### Optional argument
-l or --localhost : This is used for setting DNS to localhost (IPV4 and IPV6)

-fd FILEDNS or --filedns FILEDNS : This is used for importing DNS that using bind dns zone format. At the proccess, it will delete NS record line so there is not inconsistency DNS record.

example:
./cloudflareddos.py -d example.id -l
./cloudflareddos.py -d example.id -fd path/example.id.db

Note:
This script will do:
- Add Domain to Cloudflare
- Add DNS (localhost) or original DNS with DNS Zone DB file
- Activating I'm Under Attack
- Activating Bot Fight Mode
- Activating Firewall (3 rule)
