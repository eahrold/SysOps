#SysOps

Some simple, and hopefully useful tools.

## Observy:
Keep an eye on linux services. Plain and simple

```
Watch linux "services" and make sure their status is up and running
Usage: ./observy.py OPTIONS
Options:

Service Registration 
   -r, --register=NAME         The service to register for monitoring.
                               should be the service as declared when
                               running `/usr/sbin/service xyz status`
   -n, --no-restart            By default an attempt is made to restart a stopped service, 
                               use this flag to bypass a restart attempt.
Notification Configuration
   -w, --webhook=KIND:URL      Register a webhook url for a notification service. use like this...
                               "--webhook=slack:"https://hooks.slack.com/services/ASD...VSTH"
   --remove-webhook=KIND:URL   Remove a previouslty registered webhook (same format as above)              
Installation
   -i, --install               Install init.d script into /etc/init.d/observy
   -s, --schedule=INT          How often to check in minuets defaults to 60.
   -d, --directory=DIR         Full file path to the location where the observy.py service data is stored
                               defaults to /home/vagrant/Code/SysOps/Observy/services
   -x, --remove                Remove init.d script
Help
   -h, --help                  Show this help info

```