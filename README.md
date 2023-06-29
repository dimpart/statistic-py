# DIM Statistic Service Bot (Python)

## Usages

### 0. Clone Codes and Install Requirements

```
cd GitHub/
mkdir dimpart; cd dimpart/

git clone https://github.com/dimpart/monitor-py.git

cd monitor-py/

pip3 install -r requirements.txt
```

### 1. Create Accounts

1.0. Usages

Input command ```dimid --help``` to get help information:

```

    DIM account generate/modify

usages:
    dimid [--config=<FILE>] generate
    dimid [--config=<FILE>] modify <ID>
    dimid [-h|--help]

actions:
    generate        create new ID, meta & document
    modify <ID>     edit document with ID

optional arguments:
    --config        config file path (default: "/etc/dim/config.ini")
    --help, -h      show this help message and exit


```

1.1. Create Bot Account

Input command ```dimid --config=etc/config.ini generate``` and it would response:

```
[DB] init with config: etc/config.ini => {'database': {'public': '/var/dim/public', 'private': '/var/dim/private'}, 'station': {'host': '106.52.25.169', 'port': '9394'}, 'ans': {'statistic': ''}}
!!!    id key path: /var/dim/private/{ADDRESS}/secret.js
!!!  msg keys path: /var/dim/private/{ADDRESS}/secret_keys.js
!!!      meta path: /var/dim/public/{ADDRESS}/meta.js
!!!       doc path: /var/dim/public/{ADDRESS}/document.js
!!!     users path: /var/dim/private/users.js
!!!  contacts path: /var/dim/private/{ADDRESS}/contacts.js
!!!   members path: /var/dim/private/{ADDRESS}/members.js
Generating DIM account...
--- address types ---
    0: User
    1: Group (User Group)
    2: Station (Server Node)
    3: ISP (Service Provider)
    4: Bot (Business Node)
    5: ICP (Content Provider)
    6: Supervisor (Company President)
    7: Company (Super Group for ISP/ICP)
>>> please input address type:
```

chose ***Bot (Business Node)*** (input number "4" and enter), and it would response:

```
!!! address type: 4
!!! meta type: 1
>>> please input ID.name (default is "bot"):
```

input "stat" and enter:

```
!!! meta seed: stat
>>> please input user name: Stat Bot
>>> please input avatar url:
```

input "Stat Bot" and an image URL (can be empty), then new account will be generated:

```
!!! user info: stat@31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg "Stat Bot" 
!!! ID: stat@31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg, meta type: 1, document type: visa, name: "Stat Bot"
!!! private key: RSA, msg keys: []
[2023-06-12 16:20:41] [DB] PrivateKeyStorage >	Saving identity private key into: /var/dim/private/31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg/secret.js
[2023-06-12 16:20:41] [DB] MetaStorage >	Loading meta from: /var/dim/public/31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg/meta.js
[2023-06-12 16:20:41] [DB] MetaStorage >	Saving meta into: /var/dim/public/31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg/meta.js
[2023-06-12 16:20:41] [DB] DocumentStorage >	Loading document from: /var/dim/public/31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg/document.js
[2023-06-12 16:20:41] [DB] DocumentStorage >	Saving document into: /var/dim/public/31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg/document.js
```

the text string ```stat@31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg``` is your new bot ID.


1.2. Modify Bot Config

copy the new ID: ```stat@31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg```

open ```etc/config.ini```

```
#
#   Configuration for Bots
#

[database]
# root  = /var/dim
public  = /var/dim/public
private = /var/dim/private

[station]
host = 106.52.25.169
port = 9394

[ans]
statistic = stat@31PyFapLXhUiThUTa6Y2T5uaxWCRvLtaAg
```

1.3. Start your programming

Open codes in ***Pycharm***, starts from file ```bots/sbot_stat.py```

----
Albert Moky @ June 12, 2023
