# service-clear.py
'''
Remove a namespace from Route53 service discovery (auto-naming)
'''

from __future__ import print_function
import boto3
import time
import json
import logging
import os
from base64 import b64decode
from botocore.exceptions import ClientError


def service_discovery_result(client_service_discovery, response, service_id, msg):
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
        print('{} namespace "{}" successfully'.format(msg, service_id))
    else:
        #logger.error('{} removal from service "{}" failed with {}'.format(ip, service['Name'], result))
        print('{} namespace "{}" failed with {}'.format(msg, service_id, operation['Operation']['ErrorMessage']))

def delete_namespace(client_service_discovery, namespace_id):
    response = client_service_discovery.delete_namespace(
        Id=namespace_id
    )
    service_discovery_result(client_service_discovery, response, namespace_id, 'delete')

def get_namespace_id(client_service_discovery, namespace_name):
    response = client_service_discovery.list_namespaces(
        Filters=[
            {
                'Name': 'TYPE',
                'Values': [
                    'DNS_PRIVATE',
                ],
                'Condition': 'EQ'
            },
        ]
    )
    print(response)
    namespace_index = next((index for (index, d) in enumerate(response['Namespaces']) if d["Name"] == namespace_name), None)
    print('Namespace ID: {}'.format(response['Namespaces'][namespace_index]['Id']))
    return response['Namespaces'][namespace_index]['Id']

if __name__ == '__main__':
    try:
        client_service_discovery = boto3.client('servicediscovery')
    except ClientError as e:
        print('Client Service Discovery error: {}'.format(e.response))
    namespace_id = get_namespace_id(client_service_discovery, 'test.wiser.local')
    delete_namespace(client_service_discovery, namespace_id)
