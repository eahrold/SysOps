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

from datetime import datetime as date
from time import sleep

from notifications import NotificationManager


__version__ = '0.1'

#----------------------------------------------------------
# Service Monitor
#-------------------------------------------------------
class ServiceMonitor(object):
    '''Base class for service monitor'''

    error_bag = None

    def __init__(self, service_dir=None):
        super(ServiceMonitor, self).__init__()
        self.error_bag = []
        self._service_dir = service_dir if service_dir \
                                        else self.service_dir()

    #----------------------------------------------------------
    # Check The services
    #-------------------------------------------------------
    def check(self):
        '''Check services'''
        services = self.get_registered_services()
        success = True

        for service_dict in services:
            service = service_dict['service']
            success_string = service_dict['success_string']
            attempt_restart = service_dict['attempt_restart']

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
                          'date': date.now(),
                        }
                self.error_bag.append(error)

        return success

    #----------------------------------------------------------
    # Get/Set registered services
    #-------------------------------------------------------
    def register_service(self, service, attempt_restart):
        proc = subprocess.Popen(["/usr/sbin/service", '--status-all'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        for line in iter(proc.stdout.readline,''):
            s = line.split(']')[1].strip()
            if service == s:
                global __version__
                success_string, error, rc = self._exec_service(service, 'status')
                if rc != 0:
                    print "There was a problem registering the service (%s)" % success_string
                    return rc

                service_file = service + '.service'
                service_dict = { 'service': service,
                                 'success_string': success_string,
                                 'attempt_restart': attempt_restart,
                                 'version': __version__,
                }
                
                if not os.path.exists(self._service_dir):
                    os.makedirs(self._service_dir)

                path = os.path.join(self._service_dir, service_file)
                with open(path, 'wb') as f:
                    data = json.dumps(service_dict)
                    f.write(data)
                    f.close()
                    print "created service file: %s: %s" % (path, data)
                    return 0

        print "%s is either not currently running, or not a managed service" % service 
    
    def get_registered_services(self):
        import glob
        services = []

        service_files = glob.glob(self._service_dir+'/*.service')
        for item in service_files:
            head, file_name = os.path.split(item)
            file = open(item, 'r')
            
            json_data = json.loads(file.read())
            file.close()
        
            services.append(json_data)

        return services

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
        
    def _status(self, service):
        return self._exec_service(service, 'status')
         
    def _exec_service(self, service, cmd):
        #prints results and merges stdout and std
        p = subprocess.Popen(["/usr/sbin/service", service, cmd], stdout=subprocess.PIPE)
        (data, error) = p.communicate()
        return (data, error, p.returncode)

    @staticmethod
    def service_dir():
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'services')

def run(service_checker):
    ''' Execute the service checker process '''
    if not service_checker.check():
        notifier = NotificationManager(service_checker.error_bag);
        notifier.send()

#----------------------------------------------------------
# Install / Uninstall
#-------------------------------------------------------
def initd_script_name():
    return 'observy'

def install(schedule=60):
    ''' Install the rc.d script, register with update-rc.d
    '''
    from shutil import copyfile
    base_path = os.path.dirname(os.path.realpath(__file__))
    
    src = os.path.join(base_path, 'init.d', initd_script_name())
    dst = os.path.join('/etc/init.d', initd_script_name())
    
    data=open(src,'r').read()
    data=data.replace('{{ cur_dir_path }}', base_path)
    data=data.replace('{{ schedule_int }}', str(schedule))

    outfile=open(dst,'w')
    outfile.write(data)
    outfile.close()

    # Set the executable bit 
    os.chmod(dst, 0700);
    pipe = subprocess.PIPE

    if not os.path.isfile(dst):
        print "There was a problem copying the init.d script"
        rc = 1
    else:
        print "Starting observy system"
        try:
            rc = subprocess.check_call(['update-rc.d', '-f', initd_script_name(), 'remove'], stdout=pipe)
        except Exception as e:
            pass

        if subprocess.check_call(['update-rc.d', initd_script_name(), 'defaults'], stdout=pipe) == 0:
            rc = subprocess.check_call(["/usr/sbin/service", initd_script_name(), 'start'], stdout=pipe)
        else:
            print "There was a problem setting update-rc.d"
    return rc

def remove():
    ''' Remove from update-rc.d'''
    print "Removing the init.d script and stopping service"
    pipe = subprocess.PIPE

    try:
        subprocess.check_call(["/usr/sbin/service", initd_script_name(), 'stop'], stdout=pipe) == 0
        rc = subprocess.check_call(['update-rc.d', '-f', initd_script_name(), 'remove'], stdout=subprocess.PIPE)
        if rc == 0:
            os.remove(os.path.join('/etc/init.d/', initd_script_name()))
    except Exception as e:
        pass
        

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
Notification Configuration
   -w, --webhook=KIND:URL      Register a webhook url for a notification service. use like this...
                               "--webhook=slack:"https://hooks.slack.com/services/ASD...VSTH"
   --remove-webhook=KIND:URL   Remove a previouslty registered webhook (same format as above)              
Installation
   -i, --install               Install init.d script into /etc/init.d/observy
   -s, --schedule=INT          How often to check in minuets defaults to 60.
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
        opts, args = getopt.getopt(sys.argv[1:], "s:d:r:w:nixh", \
            [ "schedule=",
              "directory=",
              "register=",
              "webhook=",
              "remove-webhook=",
              "no-restart",
              "install",
              "remove",
              "help" ]
        )

    except getopt.GetoptError as err:
           usage(err, 2)

    service = None
    webhook = None
    remove_webhook = False

    directory = None
    schedule = None

    attempt_restart = True
    do_install = False
    do_remove = False

    for opt, arg in opts:
        if opt in ("-r", "--register"):
            service = arg
        if opt in ("-w", "--webhook"):
            webhook = arg
        if opt in ("--remove-webhook"):
            webhook = arg
            remove_webhook = True
        if opt in ("-d", "--directory"):
            directory = arg
        if opt in ("-n", "--no-restart"):
            attempt_restart = False
        if opt in ("-i", "--install"):
            do_install = True
        if opt in ("-s", "--schedule"):
            schedule = float(arg)
        if opt in ("-x", "--remove"):
            do_remove = True
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
    
    # Check for root user...
    if os.geteuid() != 0:
        exit("You need to have root privileges to run this script. Exiting.")
        sys.exit(1)
    
    if do_remove:
        rc = remove()
        sys.exit(rc)
    elif do_install:
        rc = install(schedule)
        sys.exit(rc)

    # Register Webhooks
    if webhook:
        hook = webhook.split(':', 1)
        if not remove_webhook:
            NotificationManager.register_webhook(hook[0], hook[1])
        else:
            NotificationManager.remove_webhook(hook[0], hook[1])
        sys.exit(0)
   
    service_checker = ServiceMonitor(directory)
    if service:
        rc = service_checker.register_service(service, attempt_restart)
        sys.exit(rc)
    
    if(schedule):
        while True:
            run(service_checker)
            sleep(schedule)
    else:
        run(service_checker)

    
if __name__ == "__main__":
    sys.exit(main(sys.argv))