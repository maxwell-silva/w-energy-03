import os
from dotenv import load_dotenv
import subprocess
from azure.identity import ClientSecretCredential
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor.models import DiagnosticSettingsResource, MetricSettings, LogSettings, MetricCriteria, MetricAlertResource, MetricAlertMultipleResourceMultipleMetricCriteria

# .env
load_dotenv()

resource_group_name = "w-energy-02"
vm_name = "w-energy-vm"

# Variables for authentication
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")

# Initialize clients
credentials = ClientSecretCredential(tenant_id, client_id, client_secret)

resource_client = ResourceManagementClient(credentials, subscription_id)
monitor_client = MonitorManagementClient(credentials, subscription_id)
compute_client = ComputeManagementClient(credentials, subscription_id)
workspace_id = os.getenv("WORKSPACE_ID")

def get_vm_id(resource_group_name, vm_name):
    command = f"az vm show -g {resource_group_name} -n {vm_name}"
    vm_id = subprocess.check_output(command, shell=True).decode().strip()
    return vm_id

def setup_monitoring(resource_uri):
    # Configure metrics and logs collection
    diagnostic_settings_name = 'vmDiagnosticSettings'
    diagnostic_settings = DiagnosticSettingsResource(
        metrics=[
            MetricSettings(
                category='AllMetrics',
                enabled=True,
                retention_policy=None
            )
        ],
        logs=[],
        workspace_id=workspace_id 
    )
    
    response = monitor_client.diagnostic_settings.create_or_update(
        resource_uri=resource_uri, 
        name=diagnostic_settings_name, 
        parameters=diagnostic_settings
    )
    
    print("Diagnostic Settings Response:")
    print(response)

def setup_cpu_alerts(resource_uri):
    # Set up alert rule for CPU usage > 80%
    alert_rule_name = 'Average_% Processor Time'
    criteria = MetricAlertMultipleResourceMultipleMetricCriteria(
        all_of=[
            MetricCriteria(
                name='HighCPUUsage',
                metric_name='Average_% Processor Time',
                operator='GreaterThan',
                threshold=80,
                time_aggregation='Average'
            )
        ]
    )
    alert_rule = MetricAlertResource(
        location='global',
        tags={},
        scopes=[resource_uri],
        criteria=criteria,
        description='Alert when CPU usage is greater than 80%',
        enabled=True,
        severity=3,
        window_size='PT5M',
        evaluation_frequency='PT1M'
    )
    
    response = monitor_client.metric_alerts.create_or_update(
        resource_group_name=resource_group_name, 
        rule_name=alert_rule_name, 
        parameters=alert_rule
    )

    print("Alert Rule Response:")
    print(response)

def setup_mem_alerts(resource_uri):
    # Set up alert rule for MEM usage > 75%
    alert_rule_name = 'Average_% Used Memory'
    criteria = MetricAlertMultipleResourceMultipleMetricCriteria(
        all_of=[
            MetricCriteria(
                name='HighMEMUsage',
                metric_name='Average_% Used Memory',
                operator='GreaterThan',
                threshold=75,
                time_aggregation='Average'
            )
        ]
    )
    alert_rule = MetricAlertResource(
        location='global',
        tags={},
        scopes=[resource_uri],
        criteria=criteria,
        description='Alert when MEM usage is greater than 75%',
        enabled=True,
        severity=3,
        window_size='PT5M',
        evaluation_frequency='PT1M'
    )
    
    response = monitor_client.metric_alerts.create_or_update(
        resource_group_name=resource_group_name, 
        rule_name=alert_rule_name, 
        parameters=alert_rule
    )

    print("Alert Rule Response:")
    print(response)

def list_active_alerts():
    alerts = monitor_client.alert_rules.list_by_resource_group(resource_group_name)
    for alert in alerts:
        print(f'Alert: {alert.name}, Status: {alert.properties.enabled}')

if __name__ == '__main__':
    vm = compute_client.virtual_machines.get(resource_group_name, vm_name)
    vm_id = vm.id
    resource_uri = get_vm_id(resource_group_name, vm_name)
    
    setup_monitoring(resource_uri)
    setup_GPU_alerts(resource_uri)
    setup_MEM_alerts(resource_uri)
    list_active_alerts()
