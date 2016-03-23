#!/usr/bin/python
#
# Copyright 2016 Eldon Ahrold
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import glob
import importlib
import socket

from datetime import datetime as date
from notifications import *

__version__ = '0.1'

class NotificationManager(object):
    ''' Notification Manager class responsible for running
        any defined notification class in the subdirectory.
    '''    
    def __init__(self, errors):
        super(NotificationManager, self).__init__()
        self.errors = errors
    
    def send(self):
        for c in self.notificationClasses():
            notifier = c(self.errors)
            notifier.send()

    def notificationClasses(self):
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '*Notification.py')
        paths = glob.glob(path)
        classes =[]
        for p in paths:
            class_name =  os.path.splitext(os.path.basename(p))[0]
            NotificationClass = getattr(importlib.import_module(
                                    '%s.%s' % (__name__,class_name)), class_name)

            classes.append(NotificationClass)
        return classes

    @staticmethod
    def webhooks_file():
        return os.path.join(os.path.dirname(os.path.realpath(__file__)),'webhooks.conf.json')

    @staticmethod
    def register_webhook(name, webhook):
        NotificationManager.modify_webhooks(name, webhook, True)

    @staticmethod
    def remove_webhook(name, webhook):
        NotificationManager.modify_webhooks(name, webhook, False)

    @staticmethod
    def modify_webhooks(name, webhook, add):
        webhook_file = NotificationManager.webhooks_file()
        
        if os.path.isfile(webhook_file):
            data = open(webhook_file, 'r').read()
            all_webhooks = json.loads(data)
        else:
            all_webhooks = {}

        registered_webhooks = set(all_webhooks.get(name, []))
        
        if add:
            registered_webhooks.add(webhook)
        elif webhook in registered_webhooks:
            registered_webhooks.remove(webhook)

        all_webhooks[name] = list(registered_webhooks)

        file = open(webhook_file, 'w+')
        data = json.dumps(all_webhooks, indent=2)
        file.write(data)
        file.close()

class Notifications(object):
    """Base class for service notifications"""
    errors = None
    
    def __init__(self, errors):
        super(Notifications, self).__init__()
        self.errors = errors

    def send(self):
        """Send Notification"""
        raise('Subclass must implement')

    def host_info(self):
        hostname = socket.gethostname()
        return {
            "host": hostname,
            "ip" : socket.gethostbyname(hostname),
        }

    def timestamp(self):
        return str(date.now())

class HookableNotifications(Notifications):
    """Notification class that uses webhooks"""
    _webhook_service_name = ''

    def __init__(self, errors):
        super(HookableNotifications, self).__init__(errors)

    def _all_hooks(self):
        data = open(NotificationManager.webhooks_file(), 'r').read()
        return json.loads(data)

    def webhooks(self):
        return self._all_hooks().get(self._webhook_service_name, []);

