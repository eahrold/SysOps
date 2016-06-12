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
   -f, --force                 Certian services don't show as running even when they are.
                               They may show like [?]. If you know for a fact they're running
                               use this flag to register the servcie.        
   -s, --schedule=INT          How often to check in minuets defaults to 60.
   -X, --unregister=NAME       Stop watching the service file


Notification Configuration
   -w, --webhook=KIND:URL      Register a webhook url for a notification service. use like this...
                               "--webhook=slack:"https://hooks.slack.com/services/ASD...VSTH"
   --remove-webhook=KIND:URL   Remove a previouslty registered webhook (same format as above) 

             
Installation
   -i, --install               Install init.d script into /etc/init.d/observy
   -d, --directory=DIR         Full file path to the location where the %s service data is stored
                               defaults to %s
   -x, --remove                Remove init.d script
 

Help
   -h, --help                  Show this help info
```