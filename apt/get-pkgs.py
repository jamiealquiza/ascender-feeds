#!/usr/bin/python

import apt, re, socket, sys, json, ascender
from datetime import datetime

# Vars.
ascender_address = "127.0.0.1"
ascender_port = 6030

a = ascender.Client(ascender_address, ascender_port)

# Make.
message = {}
message['@type'] = "package-ver"
message['@timestamp'] = datetime.now().isoformat()
message['hostname'] = socket.gethostname()

# Get.
packages = apt.Cache()
regexp = re.compile(".*")
for i in packages:
    if i.installed and re.match(regexp, i.name):
        message[i.installed.package.name] = i.installed.version

# Send.
a.send(json.dumps(message))
