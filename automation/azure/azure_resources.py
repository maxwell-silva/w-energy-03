import logging
import os
import json
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from azure.core.exceptions import AzureError
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.monitor.models import *
from azure.eventhub import EventHubConsumerClient
from azure.core.exceptions import HttpResponseerror

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# .env
load_dotenv()

resource_group_name = config['resource_group_name']
location = config['location']
vm_name = config['vm_name']
network_name = config['network_name']
subnet_name = config['subnet_name']
ip_name = config['ip_name']
network_interface = config['network_interface']
admin_username = os.environ.get("ADMIN_USERNAME")
admin_password = os.environ.get("ADMIN_PASSWORD")

# Logging
logging.basicConfig(filename=".logs", level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurations
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Credentials and clients
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")

credentials = ClientSecretCredential(tenant_id, client_id, client_secret)

resource_client = ResourceManagementClient(credentials, subscription_id)
compute_client = ComputeManagementClient(credentials, subscription_id)
network_client = NetworkManagementClient(credentials, subscription_id)


def create_resource_group():
    if resource_client.resource_groups.check_existence(resource_group_name):
        logger.info("Resource group already exists.")
        return
    logger.info("Creating resource group...")
    resource_group_params = {"location": location}
    resource_client.resource_groups.create_or_update(resource_group_name, resource_group_params)

def create_virtual_network():
    try:
        network_client.virtual_networks.get(resource_group_name, network_name)
        logger.info("Virtual network already exists.")
        return
    except AzureError:
        pass
    logger.info("Creating virtual network...")
    vnet_params = {
        "location": location,
        "address_space": {"address_prefixes": ["10.0.0.0/16"]}
    }
    network_client.virtual_networks.begin_create_or_update(resource_group_name, network_name, vnet_params).result()

    subnet_params = {
        "address_prefix": "10.0.10.0/24",
        "private_endpoint_network_policies": "Disabled"
    }
    network_client.subnets.begin_create_or_update(resource_group_name, network_name, subnet_name, subnet_params).result()


def create_public_ip():
    try:
        network_client.public_ip_addresses.get(resource_group_name, ip_name)
        logger.info("Public IP already exists.")
        return
    except AzureError:
        pass

    logger.info("Creating public IP...")
    ip_params = {
        "location": location,
        "public_ip_allocation_method": "Dynamic"
    }
    network_client.public_ip_addresses.begin_create_or_update(resource_group_name, ip_name, ip_params).result()


def create_network_interface():
    try:
        network_client.network_interfaces.get(resource_group_name, network_interface)
        logger.info("Network interface already exists.")
        return
    except AzureError:
        pass
    logger.info("Creating network interface...")
    subnet_info = network_client.subnets.get(resource_group_name, network_name, subnet_name)
    public_ip_info = network_client.public_ip_addresses.get(resource_group_name, ip_name)
    
    nic_params = {
        "location": location,
        "ip_configurations": [{
            "name": "ipConfig1",
            "subnet": {"id": subnet_info.id},
            "public_ip_address": {"id": public_ip_info.id}
        }]
    }
    network_client.network_interfaces.begin_create_or_update(resource_group_name, network_interface, nic_params).result()

def create_vm():
    try:
        compute_client.virtual_machines.get(resource_group_name, vm_name)
        logger.info("Virtual machine already exists.")
        return
    except AzureError:
        pass
    logger.info("Creating virtual machine...")
    nic_info = network_client.network_interfaces.get(resource_group_name, network_interface)
    
    vm_parameters = {
        "location": location,
        "hardware_profile": {
            "vm_size": "Standard_B1s"
        },
        "storage_profile": {
            "image_reference": {
                "publisher": "Canonical",
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest"
            }
        },
        "os_profile": {
            "computer_name": vm_name,
            "admin_username": admin_username,
            "admin_password": admin_password
        },
        "network_profile": {
            "network_interfaces": [{"id": nic_info.id}]
        }
    }
    compute_client.virtual_machines.begin_create_or_update(resource_group_name, vm_name, vm_parameters).result()
