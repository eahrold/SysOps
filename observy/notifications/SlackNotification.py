#!/usr/bin/env python

import subprocess
import json
import urllib2, urllib

from notifications import HookableNotifications


class SlackNotification(HookableNotifications):
    """Slack Notification class"""
    
    _webhook_service_name = 'slack'

    def __init__(self, errors):
        super(SlackNotification, self).__init__(errors)

    def send(self):
        print "Sening slack notifications"

        for error in self.errors: 
            message = error['message']
            status_code = error['status_code']
            icon_emoji = ":fire_engine:" if status_code is 3 else ":fire:"
            username = "server-notice" if status_code is 3 else "server-alert"
            host_info = self.host_info()
            
            full_message = "Alert from %s: %s at %s" % (host_info['host'], 
                                                        message,
                                                        self.timestamp()
                                                        )
            payload={
                "text": full_message,
                "icon_emoji": icon_emoji,
                "username": username,
            }

            data = urllib.urlencode(payload)

            for webhook in self.webhooks():
                try:
                    req = urllib2.Request(webhook)
                    req.add_header('Content-Type', 'application/json')
                    response = urllib2.urlopen(req, json.dumps(payload))
                except Exception as e:
                    pass

