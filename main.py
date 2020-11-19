import sys
import boto3
import time

from scripts import *

ec2_e1 = boto3.client('ec2', region_name='us-east-1')
ec2_e2 = boto3.client('ec2', region_name='us-east-2')

elb_e1 = boto3.client('elb', region_name='us-east-1')
elb_e2 = boto3.client('elb', region_name='us-east-2')

as_e1 = boto3.client('autoscaling', region_name='us-east-1')
as_e2 = boto3.client('autoscaling', region_name='us-east-2')



ubuntu_AMI_20 = 'ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-20200907'

ubuntu_AMI_name = 'ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-20201026'


def getSubnets(ec2):
    subnets = []
    sn_all = ec2.describe_subnets()
    for sn in sn_all['Subnets'] :
        subnets.append(sn['SubnetId'])
    return subnets
        
subnets_e1 = getSubnets(ec2_e1)
subnets_e2 = getSubnets(ec2_e2)

def createSecurityGroup(ec2, name):
    try: 
        security_group = ec2.create_security_group(
            Description='SecurityGroup created by Manu',
            GroupName= name,
            TagSpecifications=[
                {
                    'ResourceType': 'security-group',
                    'Tags': [
                        {
                            'Key': 'Creator',
                            'Value': 'manu'
                        },
                    ]
                },
            ]
        )
        print("Security Group {} created".format(name))
        return(security_group['GroupId'])
    except:
        deleteSecurityGroup(ec2, name)
        # print("Deletando sg que ja existe")
        # response = ec2.delete_security_group(
        # GroupName=name
        # )
        # time.sleep(10)
        return createSecurityGroup(ec2, name)


def deleteSecurityGroup(ec2, name):
    try:
        print("Deletando sg que ja existe")
        response = ec2.delete_security_group(
        GroupName=name
        )
        time.sleep(10)
    except:
        print("nada")




def updateSecurityGroupRules(ec2, groupName, port):
    response = ec2.authorize_security_group_ingress(
        GroupName=groupName,
        IpPermissions=[
            {
                'FromPort': port,
                'IpProtocol': 'tcp',
                'IpRanges': [
                    {
                        'CidrIp': '0.0.0.0/0',
                    },
                ],
                'ToPort': port,
            },
        ]
    )
    print("Security Group rules updated")


def createInstance(ami_id, ec2, instanceName, securityGroupID, UserData):
    print("Criando instância {}".format(instanceName))

    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        MaxCount=1,
        MinCount=1,
        # KeyName='manuk',
        Monitoring={
            'Enabled': True
        },
        UserData=UserData,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instanceName
                    },
                    {
                        'Key': 'Creator',
                        'Value': 'manu'
                    },
                ]
            },
        ],

        SecurityGroupIds=[
            securityGroupID,
        ],
    )
    # print((response['Reservations'][0]['Instances'][0]['PublicIpAddress']) )
    return (response["Instances"][0]['InstanceId'])

def getPublicIpAddress(ec2, InstanceId):
    response = ec2.describe_instances()
    for reservation in response["Reservations"]:
        for intance in reservation["Instances"]:
            if intance['InstanceId'] == InstanceId:
                return (intance['PublicIpAddress'])

def terminateInstances(ec2):
    response = ec2.describe_instances()
    for reservation in response["Reservations"]:   
        for intance in reservation["Instances"]:
            if(intance["State"]["Name"] != "terminated"): 
                for tags in intance["Tags"]:
                    if (tags["Key"] == "Creator"):
                        if (tags["Value"] == "manu"):
                            print("Instance terminated")
                            instanceId = (intance["InstanceId"])
                            response = ec2.terminate_instances(InstanceIds=[instanceId])
                            waiter = ec2.get_waiter('instance_terminated')
                            waiter.wait(InstanceIds=[instanceId])
                            

def createImage(ec2, instanceId, name):
    try:
        response = ec2.create_image(
            InstanceId=instanceId,
            Name=name,
            NoReboot=True
        )
        print("AMI created")
        return response['ImageId']
    except:
        print("Unregistering existing AMI") 
        imageId= getAMIid(ec2_e1, name)
        response = ec2.deregister_image(ImageId=imageId)
        return createImage(ec2, instanceId, name)


# Get AMI id by its name
def getAMIid(ec2, name):
    try:
        response = ec2.describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': [name]
                },
            ],
        )
        return response['Images'][0]['ImageId']
    except:
        print("Image not found")


def deleteLoadBalancer(elb, name):
    try:
        print("Deleting existed LoadBalancer")
        response = elb.delete_load_balancer(LoadBalancerName=name)
    except:
        print("\n")

def createLoadBalancer(elb, name, instPort, lbPort, subnets, SecurityGroup):
    # try:
        print("Creating load balancer")
        response = elb.create_load_balancer(
            LoadBalancerName=name,
            Listeners=[
                {
                    'Protocol': 'HTTP',
                    'LoadBalancerPort': lbPort,
                    'InstancePort': instPort,
                },
            ],
            Subnets=subnets,
            SecurityGroups=[SecurityGroup],
            Tags=[
                {
                    'Key': 'Creator',
                    'Value': 'manu'
                },
            ]
        )
    # except: 
    #     print("ja existe")
    #     deleteLoadBalancer(elb, name)
    #     time.sleep(10)
    #     createLoadBalancer(elb, name, instPort, lbPort, subnets, SecurityGroup)

def createAutoScaling(auto, name, InstanceId, lbName):
    try:
        response = auto.create_auto_scaling_group(
        AutoScalingGroupName=name,
        InstanceId=InstanceId,
        MinSize=1,
        MaxSize=2,
        LoadBalancerNames=[lbName],

        Tags=[
            {
                'Key': 'Creator',
                'Value': 'manu',
            },
        ],
        )
        print("AutoScaling group {} created".format(name))
    except:
        deleteAutoScaling(auto, name)
        createAutoScaling(auto, name, InstanceId, lbName)


def deleteAutoScaling(auto, name):
    try:
        print("deletando")
        response = auto.delete_auto_scaling_group(
            AutoScalingGroupName=name, ForceDelete=True)
        response = auto.delete_launch_configuration(
            LaunchConfigurationName=name)
    except:
        print("nada")





def delete_launch_configuration(auto, name):
    response = auto.describe_launch_configurations()
    for lc in response["LaunchConfigurations"]:
        if lc["LaunchConfigurationName"] == name:
            response = auto.delete_launch_configuration(
            LaunchConfigurationName=name)

def waiterInstance(ec2, instanceId):
    waiter = ec2.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instanceId])

def waiterImage(ec2, imageId):
    waiter = ec2.get_waiter('image_available')
    waiter.wait(ImageIds=[imageId])





# _________________________________TESTE INSTANCIAS________________________


# Terminate all my instances
print("___INICIO___")
terminateInstances(ec2_e1)
terminateInstances(ec2_e2)
deleteAutoScaling(as_e1, 'AutoScalingManu')
deleteLoadBalancer(elb_e1, 'lbManu')
delete_launch_configuration(as_e1, "AutoScalingManu")
time.sleep(10)
print("_____1")
deleteSecurityGroup(ec2_e1, 'sgManu1')
print("_____2")
deleteSecurityGroup(ec2_e2, 'sgManu2')

time.sleep(10)
#delete security grooup


print("___INICIO___")
# Creating a Security Group
print("Criando security group e2")
postgres_SGroupID = (createSecurityGroup(ec2_e2, 'sgManu2'))
print("___")
print("Criando security group e1")
django_SGroupID = (createSecurityGroup(ec2_e1, 'sgManu1'))
print("___")
time.sleep(20)
print(postgres_SGroupID)
print(django_SGroupID)


print("Atualizando regras")
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 22)
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 5432)
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 8080)
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 80)
print("___")
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 22)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 5432)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 8080)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 80)


# Getting ubuntu_20 AMI id 
AMI_ID_ubuntu_20_e1 = (getAMIid(ec2_e1, ubuntu_AMI_name))
AMI_ID_ubuntu_20_e2 = (getAMIid(ec2_e2, ubuntu_AMI_name))

print("___POSTGRES___")
# Creating an instance 
postgres_instanceId = createInstance(AMI_ID_ubuntu_20_e2, ec2_e2, 'PostgresManu ', 'sgManu2', postgres_script)
waiterInstance(ec2_e2, postgres_instanceId)

PublicIpAddress = getPublicIpAddress(ec2_e2, postgres_instanceId)

print("PublicIpAddress {}".format(PublicIpAddress))



print("___DJANGO___")
django_script = (django_script(PublicIpAddress))

django_instanceId = createInstance(AMI_ID_ubuntu_20_e1, ec2_e1, 'DjangoManu ', 'sgManu1', django_script)
waiterInstance(ec2_e1, django_instanceId)


# Creating load balancer
createLoadBalancer(elb_e1, 'lbManu', 8080, 8080, subnets_e1, django_SGroupID )

createAutoScaling(as_e1, 'AutoScalingManu', django_instanceId, 'lbManu')



# _________________________________________________________________________



# print("FIM DOS TESTES")
# terminateInstances(ec2_e1)
# # deleteAutoScaling(as_e1, 'AutoScalingManu') #da erro se nao existe mas tudo bem (nao vou usar isso)
# # deleteLoadBalancer(elb_e1, 'lbManu')


print("FIM TESTE")
