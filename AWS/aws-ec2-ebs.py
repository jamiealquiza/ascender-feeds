#!/usr/local/bin/python3

from pprint import pprint
from boto import ec2
from queue import Queue
import socket, sys, os, threading, time, logging

# AWS vars.
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
# Config vars.
ascender_address = "127.0.0.1"
ascender_port = 6030
query_threads = 8
ascend_threads = 2
# General vars / objects.
q_query = Queue()
q_ascend = Queue(512)

# Logging config.
log = logging.getLogger()
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(fmt='%(asctime)s | %(levelname)s | %(message)s'))
log.addHandler(handler)
log.setLevel(logging.INFO)


def stringify(input):
    """Iterates over dict and converts k/v pairs to strings (excluding ints)."""
    if isinstance(input, dict):
        return dict((stringify(key), stringify(value)) for key, value in input.items())
    elif isinstance(input, list):
        return [stringify(element) for element in input]
    elif type(input) == int:
        return input
    else:
        return str(input)

def ascend():
    """Sends message to Ascender."""
    while True:
        msg = q_ascend.get()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ascender_address, ascender_port))
        s.sendall(bytes(msg, 'UTF-8'))
        while 1:
            resp = s.recv(256)
            if resp != b'':
                continue
                #print("%s" % resp.decode("utf-8").rstrip())
            else:
                resp += s.recv(256)
                break
        s.close()
        q_ascend.task_done()

def query_region():
    """Pulls EC2 and EBS metadata from region and combines/filters."""
    # Pull region from queue and handle.
    while True:
        region = q_query.get()
        log.info("Querying region: %s" % region)
        t_start = time.time()
        ec2conn = ec2.connect_to_region(region,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        # Get volumes.
        vols = ec2conn.get_all_volumes()
        # Create array with volume dictionaries.
        volumes = []
        for i in vols:
            volumes.append(stringify(i.__dict__))

        for i in volumes:
            # Set type for Langolier.
            i['@type'] = "aws-ebs"

            # Format for Ascender.
            msg = str(i).replace("\'", "\"")
            # Write to Ascender.
            q_ascend.put(msg)

        # Get EC2 instances.
        reservations = ec2conn.get_all_instances()
        instances = [i for r in reservations for i in r.instances]

        # Create dict for volume lookup by id to associate with instances.
        volume = {}
        for i in vols:
            volume[i.id] = i.__dict__

        # Pull instance data.
        for i in instances:
            meta = i.__dict__
            # Set type for Langolier.
            meta['@type'] = "aws-ec2"
            # Find EBS volumes associated with instance and add to 'vols' key.
            meta['vols'] = {}
            for i in meta['block_device_mapping'].keys():
                meta['vols'][i] = volume[meta['block_device_mapping'][i].volume_id]
            # Add a 'storage_total' (sum of all associated EBS size attributes) key.
            meta['storage_total'] = 0
            for i in meta['vols'].keys():
                meta['storage_total'] += meta['vols'][i]['size']

            # Format for Ascender.
            msg = str(stringify(meta)).replace("\'", "\"")
            # Write to Ascender.
            q_ascend.put(msg)

        # Work done for region.
        t_delta = round(time.time() - t_start, 2)
        log.info("Region done: %s in %s sec." % (region, t_delta))
        q_query.task_done()


# Init query thread pool.
for i in range(query_threads):
    t = threading.Thread(target=query_region)
    t.daemon = True
    t.start()

# Init Ascender sending pool.
for i in range(ascend_threads):
    t = threading.Thread(target=ascend)
    t.daemon = True
    t.start()

def main():
    # Regions to query.
    regions = ['us-west-1', 'us-west-2', 'us-east-1']
    for r in regions: q_query.put(r)
    q_query.join()

if  __name__ =='__main__': main()
