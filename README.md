# Distributed System Project  
## Distributed File System

### prepare
create user in /Servers/user.txt
```
username password
...
```
create server files in /Servers/ServerFiles/

### start:
use bash scripts:
```bash
cd DistributedSystem-project-main/
bash server_start.sh
bash client_start.sh
```
or
```bash
cd DistributedSystem-project-main/
# servers
python ./Servers/servers.py --n 3
# proxy server
python ./Servers/proxy.py
# client
start python ./Client/client.py --username user1 --password 123
start python ./Client/client.py --username user2 --password 123
...
```