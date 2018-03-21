# service-clear.py
'''
Remove all instances from a Route53 service discovery (auto-naming) service
'''

from __future__ import print_function
import boto3
import time
import json
import logging
import os
from base64 import b64decode
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def service_discovery_result(client_service_discovery, response, service_id, instance_id, msg):
    #logger.debug(response)
    print(response)
    count = 0
    operation = client_service_discovery.get_operation(OperationId=response['OperationId'])
    while operation['Operation']['Status'] not in ['FAIL', 'SUCCESS']:
        count += 1
        print('Waiting for result status: {}'.format(count))
        time.sleep(1)
        operation = client_service_discovery.get_operation(OperationId=response['OperationId'])
    print(operation)
    if operation['Operation']['Status'] == 'SUCCESS':
        #logger.info('{} removed from service "{}" successfully'.format(ip, service['Name']))
        print('{} {} with service "{}" successfully'.format(instance_id, msg, service_id))
    else:
        #logger.error('{} removal from service "{}" failed with {}'.format(ip, service['Name'], result))
        print('{} {} with service "{}" failed with {}'.format(instance_id, msg, service_id, operation['Operation']['ErrorMessage']))

def service_id(client_service_discovery, service_name):
    # Get service record
    response = client_service_discovery.list_services()
    service_index = next((index for (index, d) in enumerate(response['Services']) if d["Name"] == service_name), None)
    #logger.debug('Service at index: {}'.format(service_index))
    print('Service: {}'.format(response['Services'][service_index]))
    return response['Services'][service_index]['Id']

if __name__ == '__main__':
    try:
        client_service_discovery = boto3.client('servicediscovery')
    except ClientError as e:
        print('Client Service Discovery error: {}'.format(e.response))
    service_id = service_id(client_service_discovery, 'datadog')
    print('Service ID: '.format(service_id))
    for instance in client_service_discovery.list_instances(ServiceId=service_id)['Instances']:
        print(instance)
        response = client_service_discovery.deregister_instance(
            ServiceId=service_id,
            InstanceId=instance['Id']
        )
        service_discovery_result(client_service_discovery, response, service_id, instance['Id'], 'deregister')
    print(client_service_discovery.list_instances(ServiceId=service_id))
