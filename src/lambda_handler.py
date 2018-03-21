
# lambda-service-discovery
'''
Designed to be triggered by AWS CloudWatch ECS status change events
Then register/deregister container instance in Route53 auto-naming service
'''
# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_cwe_events.html

from __future__ import print_function
import boto3
import time
import json
import logging
import os
from base64 import b64decode
from botocore.exceptions import ClientError

'''
This gives you the container instances each task is running on:
aws ecs list-tasks --query "taskArns" --output text | xargs aws ecs describe-tasks --query "tasks[].taskArn,taskDefinitionArn,containerInstanceArn" --tasks

This gives you the EC2 instance's IP addresses for reach container instance:
aws ecs list-container-instances --query "containerInstanceArns" --output text | xargs aws ecs describe-container-instances --container-instances --query "containerInstances[]..Instanceshttp://].NetworkInterfaces[.Association[].PublicIp" --output text --instance-ids
'''

# load the logging configuration. Can use: ini, json. yaml
#logging.config.fileConfig('logging.ini')
# Allow setting from ENV: level
#logger = logging.getLogger(__name__)
#logging.setLevel(logging.DEBUG)
# create a logging format
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# '%(asctime)s %(levelname)s %(name)s: %(message)s'
#handler.setFormatter(formatter)
# add the handlers to the logger
#logger.addHandler(handler)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def service_discovery_result(client_service_discovery, response, service, ip, msg):
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
        print('{} {} with service "{}" successfully'.format(ip, msg, service['Name']))
    else:
        #logger.error('{} removal from service "{}" failed with {}'.format(ip, service['Name'], result))
        print('{} {} with service "{}" failed with {}'.format(ip, msg, service['Name'], operation['Operation']['ErrorMessage']))
    print(client_service_discovery.list_instances(ServiceId=service['Id']))

def action_deregister(client_service_discovery, service, id, ip):
    '''
    Deregister (remove) from service discovery service
    '''
    # log removing ip from service
    response = client_service_discovery.deregister_instance(
        ServiceId=service['Id'],
        InstanceId=id
    )
    service_discovery_result(client_service_discovery, response, service, ip, 'deregister')
    #logger.debug(response)
    #print(response)
    #result = service_discovery_result(response)
    #if result == 200:
    #    #logger.info('{} removed from service "{}" successfully'.format(ip, service['Name']))
    #    print('{} removed from service "{}" successfully'.format(ip, service['Name']))
    #else:
    #    #logger.error('{} removal from service "{}" failed with {}'.format(ip, service['Name'], result))
    #    print('{} removal from service "{}" failed with {}'.format(ip, service['Name'], result))

def action_noop(client_service_discovery, service, ip):
    '''
    Do nothing. For status that is not cause for add or remove
    '''
    print('NOOP')

def action_register(client_service_discovery, service, id, ip):
    '''
    Register (add) to service discovery service
    '''
    # log adding ip to service
    response = client_service_discovery.register_instance(
        ServiceId=service['Id'],
        InstanceId=id,
        Attributes={
            'AWS_INSTANCE_IPV4': ip
        }
    )
    service_discovery_result(client_service_discovery, response, service, ip, 'register')
    #logger.debug(response)
    #print(response)
    #result = service_discovery_result(response)
    #if result == 200:
    #    #logger.info('{} added to service "{}" successfully'.format(ip, service['Name']))
    #    print('{} added to service "{}" successfully'.format(ip, service['Name']))
    #else:
    #    #logger.error('{} addition to service "{}" failed with {}'.format(ip, service['Name'], result))
    #    print('{} addition to service "{}" failed with {}'.format(ip, service['Name'], result))

def get_instance_ip(cluster, instance):
    '''
    Get the IP address of the EC2 instance the task in running on
    '''
    # Get EC2 IP
    print('ECS Cluster: {}, ECS Instance: {}'.format(cluster, instance))
    try:
        client_ecs = boto3.client('ecs')
    except ClientError as e:
        print('Client ECS error: {}'.format(e.response))
    container_instances = client_ecs.describe_container_instances(
        cluster=cluster,
        containerInstances=[
            instance,
        ]
    )
    #print(container_instances)
    # FIX: not getting EC2 that task is on
    ec2_id = container_instances['containerInstances'][0]['ec2InstanceId']
    #logger.debug("EC2 Container Instance ID: " + ec2_id)
    print("EC2 Container Instance ID: " + ec2_id)
    try:
        client_ec2 = boto3.client('ec2')
    except ClientError as e:
        print('Client EC2 error: {}'.format(e.response))
    print('After EC2 Client created')
    ec2 = client_ec2.describe_instances(
        InstanceIds=[
            ec2_id,
        ],
    )
    #print(ec2)
    ip = ec2['Reservations'][0]['Instances'][0]['PrivateIpAddress']
    #logger.info('EC2 Container Instance IP: {}'.format(ip))
    print('EC2 Container Instance IP: {}'.format(ip))
    return ip

def process_event(message):
    '''
    Process ECS event message
    '''
    # Only process Task change events
    if message['detail-type'] != 'ECS Task State Change':
        logger.info('Not processing event type: {}'.format(message['detail-type']))
        print('Not processing event type: {}'.format(message['detail-type']))
        return

    detail   = message['detail']

    cluster  = detail['clusterArn']
    instance = detail['containerInstanceArn']
    task     = detail['taskArn']
    status_desired   = detail['desiredStatus']
    status_last   = detail['lastStatus']
    status_last_con   = detail['containers'][0]['lastStatus']
    service  = detail['group'] # parse or use override
    #logger.debug('{} {} {} {} {}'.format(cluster, instance, task, status, service))
    print('ECS Cluster: {}\n ECS Instance: {}\n ECS Task: {}\n Service: {}\n StatusD: {}\n StatusL: {}\n StatusLC: {}'.format(cluster, instance, task, service, status_desired, status_last, status_last_con))
    if 'stoppedReason' in detail:
        print('Stop reason: {}'.format(detail['stoppedReason']))
    service_name = service[service.index(':', 0, len(service)) + 1 :len(service)]
    #logger.info("Service name: " + service_name)
    print("Service name: " + service_name)
    task_id = task[task.index('/', 0, len(task)) + 1 : len(task)]
    print('Task ID: {}'.format(task_id))
    if all(v == 'RUNNING' for v in [status_desired, status_last, status_last_con]):
        status = 'RUNNING'
    elif status_desired == 'STOPPED' and 'stoppedReason' in detail and all(v == 'RUNNING' for v in [status_last, status_last_con]):
        status = 'STOPPED'
    else:
        print('Nothing to do')
        return
    print('Update for status: {}'.format(status))
    # Update Route53 service
    update = {
        'STOPPED'  : action_deregister,
        'RUNNING'  : action_register,
        'PENDING'  : action_noop
    }

    ip = get_instance_ip(cluster, instance)

    print('Before service discovery client')
    try:
        client_service_discovery = boto3.client('servicediscovery')
    except ClientError as e:
        print('Client Service Discovery error: {}'.format(e.response))
    print('After service discovery client')
    # Get service record
    response = client_service_discovery.list_services()
    service_index = next((index for (index, d) in enumerate(response['Services']) if d["Name"] == service_name), None)
    #logger.debug('Service at index: {}'.format(service_index))
    print('Service at index: {}'.format(service_index))
    service = response['Services'][service_index]

    service_discovery_instance_id = 'ecs-{}-{}-{}'.format(service['Name'], ip, task_id)
    print('Service discovery instance ID: {}'.format(service_discovery_instance_id))
    #logger.debug('{} {}'.format(service['Name'], service['Id']))
    print('{} {}'.format(service['Name'], service['Id']))
    update[status](client_service_discovery, service, service_discovery_instance_id, ip)
    print('After update service discovery')

def lambda_handler(event, context):
    '''
    Process incoming events
    '''
    # Allow different config file to be specified
    if 'LAMBDA_CONFIG' in os.environ:
        config = json.loads(os.getenv('LAMBDA_CONFIG'))
    else:
        with open('config.json') as f:
            config = json.load(f)
    # Replace config data with environment data if it exists
    # Environment variables are keys uppercased
    for key in config.keys():
        if key.upper() in os.environ:
            config[key] = os.getenv(key.upper())
    print("Config: " + json.dumps(config, indent=2))

    # Setup logging
    log_level = getattr(logging, config["log_level"].upper(), None)
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: {}'.format(config["log_level"]))
    logger.setLevel(log_level)
    #logging.basicConfig(format='%(levelname)s:%(message)s', level=log_level)

    print("Received event: " + json.dumps(event, indent=2))
    # logging working local but not in lambda
    #logger.info("===============Start work=================")
    print("===============Start work=================")

    # Only process ECS events
    if 'source' in event and event['source'] == 'aws.ecs':
        process_event(event)
    else:
        #logger.warning("Unknown event")
        print("Unknown event")

    return 'Done'

# Local testing
if __name__ == '__main__':
    event_template = json.loads(r"""
{
  "version": "0",
  "id": "9bcdac79-b31f-4d3d-9410-fbd727c29fab",
  "detail-type": "ECS Task State Change",
  "source": "aws.ecs",
  "account": "111122223333",
  "time": "2016-12-06T16:41:06Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:ecs:us-west-2:105667981759:task/32efc720-039e-4f5c-bad1-51d62dac690b"
  ],
  "detail": {
    "clusterArn": "arn:aws:ecs:us-west-2:105667981759:cluster/one-test-one",
    "containerInstanceArn": "arn:aws:ecs:us-west-2:105667981759:container-instance/e0331acb-dfa5-436b-9041-237ff97e2f02",
    "containers": [
      {
        "containerArn": "arn:aws:ecs:us-east-1:111122223333:container/3305bea1-bd16-4217-803d-3e0482170a17",
        "exitCode": 0,
        "lastStatus": "STOPPED",
        "name": "datadog",
        "taskArn": "arn:aws:ecs:us-west-2:105667981759:task/32efc720-039e-4f5c-bad1-51d62dac690b"
      }
    ],
    "createdAt": "2016-12-06T16:41:05.702Z",
    "desiredStatus": "RUNNING",
    "group": "service:datadog",
    "lastStatus": "RUNNING",
    "overrides": {
      "containerOverrides": [
        {
          "name": "datadog"
        }
      ]
    },
    "startedAt": "2016-12-06T16:41:06.8Z",
    "startedBy": "ecs-svc/9223370556150183303",
    "updatedAt": "2016-12-06T16:41:06.975Z",
    "taskArn": "arn:aws:ecs:us-west-2:105667981759:task/32efc720-039e-4f5c-bad1-51d62dac690b",
    "taskDefinitionArn": "arn:aws:ecs:us-east-1:111122223333:task-definition/xray:2",
    "version": 4
  }
}""")
    print('Local testing')
    print(lambda_handler(event_template, None))
