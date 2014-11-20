#!/usr/local/bin/python3

from pprint import pprint
from boto import ec2
import socket
import os


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

AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']

def pull_region(region):
    """Pulls EC2 and EBS metadata from region and combines/filters."""
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
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 6030))

        # Set type for Langolier.
        i['@type'] = "aws-ebs"

        # Format for Ascender.
        msg = str(i).replace("\'", "\"")
        s.sendall(bytes(msg, 'UTF-8'))
        while 1:
            resp = s.recv(4096)
            if resp != b'':
                print("Ascender response: %s" % resp.decode("utf-8"))
            else:
                resp += s.recv(4096)
                break
        s.close()

    # Get EC2 instances.
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]

    # Create dict for volume lookup by id to associate with instances.
    volume = {}
    for i in vols:
        volume[i.id] = i.__dict__

    for i in instances:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 6030))
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
        s.sendall(bytes(msg, 'UTF-8'))
        while 1:
            resp = s.recv(4096)
            if resp != b'':
                print("Ascender response: %s" % resp.decode("utf-8"))
            else:
                resp += s.recv(4096)
                break
        s.close()

def main():
    # Regions to query.
    regions = ['us-west-1', 'us-west-2', 'us-east-1']
    for r in regions: pull_region(r)

if  __name__ =='__main__': main()
