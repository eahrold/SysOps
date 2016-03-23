#!/usr/bin/env python

# MIT License

# Copyright (c) 2016 Eldon Ahrold

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os, sys, getopt, subprocess
import json
import syslog

from datetime import datetime, timedelta
from time import sleep

from notifications import NotificationManager


__version__ = '0.1'

#----------------------------------------------------------
# Service Monitor
#-------------------------------------------------------
class ServiceMonitor(object):
    '''Base class for service monitor'''

    error_bag = None
    _last_checks = None

    _localizables = {
        'err.reg': "There was a problem registering the service (%s)",
        'not.running': "%s is either not currently running, or not a managed service",
        'new.serv': "Created service file: %s:\n%s",

        'rem.serv': "Removing %s service file",
        'err.rem.serv': "Error Removing the service file",
        'not.reg': "%s service isn't registered",
    }
    
    def __init__(self, service_dir=None):
        super(ServiceMonitor, self).__init__()
        self.error_bag = []
        self._service_dir = service_dir if service_dir \
                                        else self.service_dir()
        self._last_checks = {}

    #----------------------------------------------------------
    # Check The services
    #-------------------------------------------------------
    def check(self):
        '''Check services'''
        self.error_bag = []
        services = self.get_registered_services()
        success = True

        for service_dict in services:
            service = service_dict['service']
            success_string = service_dict['success_string']
            attempt_restart = service_dict.get('attempt_restart', True)
            check_interval = service_dict.get('check_interval', 60)

            if self._should_check(service, check_interval):
                print "Checking %s" % service
                out, err, rc = self._status(service);

                internal_rc = 0 if out == success_string else 1
                if internal_rc is not 0:
                    success = False
                    if attempt_restart:
                        if self._start(service) != 0:
                            rc = 2        
                        else:
                            internal_rc = 3
                    
                    error = { 'status_code': internal_rc,
                              'message': self._status_message(service, internal_rc),
                              'date': str(datetime.now()),
                            }
                    self.error_bag.append(error)
        return success

    #----------------------------------------------------------
    # Get/Set registered services
    #-------------------------------------------------------
    def register_service(self, service, interval=60, attempt_restart=True):
        global __version__

        for s in self._service_list()[0]:
            if service != s:
                continue

            success_string, error, rc = self._exec_service(service, 'status')
            if rc != 0:
                print self._localizables['err.reg'] % success_string
                return rc

            service_file = service + '.service'
            service_dict = { 
                'service': service,
                'success_string': success_string,
                'attempt_restart': attempt_restart,
                'check_interval': interval or 60,
                'version': __version__,
            }
            
            if not os.path.exists(self._service_dir):
                os.makedirs(self._service_dir)

            path = os.path.join(self._service_dir, service_file)
            with open(path, 'wb') as file:
                data = json.dumps(service_dict, indent=2)
                file.write(data)
                file.close()
                print self._localizables['new.serv'] % (path, data) 
                return 0

        print self._localizables['not.running'] % service 
    
    def remove_service(self, service):
        service_file = service + '.service'
        path = os.path.join(self._service_dir, service_file)
        if os.path.isfile(path):
            try: 
                print self._localizables['rem.serv'] % service 
                os.remove(path)
            except Exception as e:
                print self._localizables['err.rem.serv'] 
                return 1
        else:
            print self._localizables['not.reg'] % service 
        return 0


    def get_registered_services(self):
        import glob
        services = []
        service_files = glob.glob(self._service_dir+'/*.service')
        for item in service_files:
            data = open(item, 'r').read()
            services.append(json.loads(data))
        return services

    #----------------------------------------------------------
    # Util
    #-------------------------------------------------------
    def _should_check(self, service, interval):
        # Do the date compare routine 
        now = datetime.now()
        last_check = self._last_checks.get(service);
        
        should =  not last_check or \
            ((now - last_check) > timedelta(minutes=interval))

        if should:
            # if we should check update the timestamp to now
            self._last_checks[service] = now;
        return should


    #----------------------------------------------------------
    # Message
    #-------------------------------------------------------
    def _status_message(self, service, rc):
        message = 'is online and running smooth'
        if rc == 1:
            message = 'was offline'
        elif rc == 2:
            message = 'was offline, and restart failed'
        elif rc == 3:
            message = 'was offline, but was successfully restarted'
        
        return '%s %s' % (service, message)


    #---------------------------------------------------------
    # Subprocess
    #------------------------------------------------------
    def _start(self, service):
        return self._exec_service(service, 'start')[2]

    def _stop(self, service):
        return self._exec_service(service, 'stop')[2]

    def _status(self, service):
        return self._exec_service(service, 'status')

    def _service_list(self):
        running = []
        stopped = []
        procs = self._status_all()
        for r in procs[0]:
            running.append(r.split(']')[1].strip())
        for e in procs[1]:
            stopped.append(r.split(']')[1].strip())

        return (running, stopped)

    def _status_all(self):
        proc = subprocess.Popen(
            ["/usr/sbin/service", '--status-all'],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        (data, error) = proc.communicate()
        return (data.splitlines(), error.splitlines())

    def _exec_service(self, service, cmd):
        proc = subprocess.Popen(
            ["/usr/sbin/service", service, cmd], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        (data, error) = proc.communicate()
        return (data, error, proc.returncode)

    @staticmethod
    def service_dir():
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'services')

def run(service_checker, keep_alive=False):
    ''' Execute the service checker process '''
    i = 0
    while True:
        if not service_checker.check():
            notifier = NotificationManager(service_checker.error_bag);
            notifier.send()
        if not keep_alive: break
        sleep(1)

#----------------------------------------------------------
# Install / Uninstall
#-------------------------------------------------------
def initd_script_name():
    return 'observy'

def install(service_data_dir):
    ''' Install the rc.d script, register with update-rc.d
    '''
    from shutil import copyfile
    base_path = os.path.dirname(os.path.realpath(__file__))
    
    src = os.path.join(base_path, 'init.d', initd_script_name())
    dst = os.path.join('/etc/init.d', initd_script_name())
    
    data=open(src,'r').read()
    
    data=data.replace('{{ exec_dir_path }}', base_path)
    data=data.replace('{{ service_data_dir }}', 
        service_data_dir or ServiceMonitor.service_dir())

    outfile=open(dst,'w')
    outfile.write(data)
    outfile.close()

    # Set the executable bit 
    os.chmod(dst, 0700);
    stdout = subprocess.PIPE
    stderr = subprocess.PIPE

    if not os.path.isfile(dst):
        print "There was a problem copying the init.d script"
        rc = 1
    else:
        print "Starting observy system"
        try:
            rc = subprocess.check_call(
                ['update-rc.d', '-f', initd_script_name(), 'remove'], 
                stdout=stdout
            )
        except Exception as e:
            pass

        # register the service
        update_cmd = ['update-rc.d', initd_script_name(), 'defaults'] 
        if subprocess.check_call(update_cmd, stdout=stdout) == 0:
            # fire up the service
            service_start_cmd = ["/usr/sbin/service", initd_script_name(), 'start']
            rc = subprocess.check_call(service_start_cmd, stdout=stdout)
        else:
            print "There was a problem setting update-rc.d"
    return rc

def remove():
    ''' Remove from update-rc.d'''
    print "Removing the init.d script and stopping service"
    stdout = subprocess.PIPE

    try:
        # Stop the service
        service_stop_command = ["/usr/sbin/service", initd_script_name(), 'stop']
        subprocess.check_call(service_stop_command, stdout=stdout) == 0

        # Remove from registry
        remove_cmd = ['update-rc.d', '-f', initd_script_name(), 'remove']
        rc = subprocess.check_call(remove_cmd, stdout=stdout)
        if rc == 0:
            # Finally delete the init.d file
            os.remove(os.path.join('/etc/init.d/', initd_script_name()))
    except Exception as e:
        print "There was a problem removing the init.d script"
        raise e
        

#----------------------------------------------------------
# Usage
#-------------------------------------------------------
def usage(err=None, returncode=0):
    ''' Print out general usage for module '''

    global __version__
    exec_name = os.path.basename(__file__)
    
    if(err):
        print str(err)

    print '%s version %s' % (exec_name, __version__)
    print '''Watch linux "services" and make sure their status is up and running'''
    print '''Usage: %s OPTIONS''' % (__file__)
    print '''Options:

Service Registration 
   -r, --register=NAME         The service to register for monitoring.
                               should be the service as declared when
                               running `/usr/sbin/service xyz status`
   -n, --no-restart            By default an attempt is made to restart a stopped service, 
                               use this flag to bypass a restart attempt.
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
''' % (exec_name, ServiceMonitor.service_dir())
    # Exit out
    sys.exit(returncode)

#----------------------------------------------------------
# Main
#-------------------------------------------------------
def main(argv):
    '''Main method'''
    # getopts   
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:d:r:w:K:X:niDxh", \
            [ "schedule=",
              "directory=",
              "register=",
              "webhook=",
              "remove-webhook=",
              "no-restart",
              "install",
              "remove",
              "daemon",
              "help" ]
        )

    except getopt.GetoptError as err:
           usage(err, 2)

    service = None
    remove_service = False

    webhook = None
    remove_webhook = False

    directory = None
    schedule = None

    attempt_restart = True
    install_initd = False
    remove_initd = False

    daemonize = False

    for opt, arg in opts:
        if opt in ("-r", "--register"):
            service = arg
        if opt in ("-s", "--schedule"):
            schedule = float(arg)
        if opt in ("-n", "--no-restart"):
            attempt_restart = False
        if opt in ("-X", "--unregister"):
            service = arg
            remove_service = True

        if opt in ("-w", "--webhook"):
            webhook = arg
        if opt in ("-K", "--remove-webhook"):
            webhook = arg
            remove_webhook = True

        if opt in ("-i", "--install"):
            install_initd = True
        if opt in ("-d", "--directory"):
            directory = arg
        if opt in ("-x", "--remove"):
            remove_initd = True
        if opt in ("-D", "--daemon"):
            daemonize = True
        
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
    
    # Check for root user...
    if os.geteuid() != 0:
        exit("You need to have root privileges to run this script. Exiting.")
        sys.exit(1)
    
    if remove_initd:
        rc = remove()
        sys.exit(rc)
    elif install_initd:
        rc = install(directory)
        sys.exit(rc)

    # Register Webhooks
    if webhook:
        hook = webhook.split(':', 1)
        if not remove_webhook:
            NotificationManager.register_webhook(hook[0], hook[1])
        else:
            NotificationManager.remove_webhook(hook[0], hook[1])
        sys.exit(0)
   
    # Add Remove servcies
    service_checker = ServiceMonitor(directory)
    if service:
        if remove_service:
            rc = service_checker.remove_service(service)
        else:
            rc = service_checker.register_service(service, schedule, attempt_restart)
        sys.exit(rc)
    
    # Run
    sys.exit(run(service_checker, keep_alive=daemonize))

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt as e:
        print '\nStopping monitor...'
        sys.exit(0)
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, "Excepton %s" % e)

