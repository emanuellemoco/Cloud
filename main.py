import sys
import boto3
from scripts import *
from color import *

ec2_e1 = boto3.client('ec2', region_name='us-east-1')
ec2_e2 = boto3.client('ec2', region_name='us-east-2')
elb_e1 = boto3.client('elb', region_name='us-east-1')
as_e1 = boto3.client('autoscaling', region_name='us-east-1')

ubuntu18_AMI = 'ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-20201026'

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
        print(Color.F_LightGreen,"Security Group {} criado".format(name),Color.F_Default)
        return(security_group['GroupId'])
    except:
        deleteSecurityGroup(ec2, name)
        return createSecurityGroup(ec2, name)


def deleteSecurityGroup(ec2, name):
    try:
        response = ec2.delete_security_group(GroupName=name)
        print(Color.F_LightRed,"Security Group {} deletado".format(name),Color.F_Default)
    except:
        pass

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
    # print("Security Group {} regras atualizadas".format(groupName))
    print(Color.F_LightYellow,"Security Group {} regras atualizadas".format(groupName),Color.F_Default)


def createInstance(ami_id, ec2, instanceName, securityGroupID, UserData):
    print(Color.F_LightGreen,"Criando instância {}".format(instanceName),Color.F_Default)
    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        MaxCount=1,
        MinCount=1,
        # KeyName='manuk',
        Monitoring={'Enabled': True},
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
        SecurityGroupIds=[securityGroupID],
    )
    print(Color.F_LightGreen,"Instância {} criada".format(instanceName),Color.F_Default)
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
                            instanceId = (intance["InstanceId"])
                            response = ec2.terminate_instances(InstanceIds=[instanceId])
                            print(Color.F_LightRed,"Instancia terminada",Color.F_Default)
                            waiter = ec2.get_waiter('instance_terminated')
                            waiter.wait(InstanceIds=[instanceId])
                            
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
        print("Imagem não encontrada")


def deleteLoadBalancer(elb, name):
    try:
        elb.delete_load_balancer(LoadBalancerName=name)
        print(Color.F_LightRed,"LoadBalancer {} deletado".format(name),Color.F_Default)
    except:
        pass

def createLoadBalancer(elb, name, instPort, lbPort, subnets, SecurityGroup):
    try:
        print(Color.F_LightYellow,"Criando Load Balancer {}".format(name),Color.F_Default)
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
        print(Color.F_LightGreen,"Load Balancer {} criado".format(name),Color.F_Default)
        return response["DNSName"]
    except: 
        deleteLoadBalancer(elb, name)
        createLoadBalancer(elb, name, instPort, lbPort, subnets, SecurityGroup)

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
        print(Color.F_LightYellow,"AutoScaling group {} created".format(name),Color.F_Default)
    except:
        deleteAutoScaling(auto, name)
        createAutoScaling(auto, name, InstanceId, lbName)

def deleteAutoScaling(auto, name):
    try:
        response = auto.delete_auto_scaling_group(AutoScalingGroupName=name, ForceDelete=True)
        print(Color.F_LightRed,"AutoScaling {} deletado".format(name),Color.F_Default)

        response = auto.delete_launch_configuration(LaunchConfigurationName=name)
        print(Color.F_LightRed,"Launch configuration {} deletado".format(name),Color.F_Default)

    except:
        pass


def waiterInstance(ec2, instanceId):
    waiter = ec2.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instanceId])


#_______________________________________
# Terminate all my instances
print(Color.F_LightBlue,"Preparando o ambiente!",Color.F_Default)
terminateInstances(ec2_e1)
terminateInstances(ec2_e2)
deleteAutoScaling(as_e1, 'AutoScalingManu')
deleteLoadBalancer(elb_e1, 'lbManu')
deleteSecurityGroup(ec2_e1, 'sgManu1')
deleteSecurityGroup(ec2_e2, 'sgManu2')

# print("_________NICIO_________")
# Creating a Security Group
postgres_SGroupID = (createSecurityGroup(ec2_e2, 'sgManu2'))
django_SGroupID = (createSecurityGroup(ec2_e1, 'sgManu1'))

# print(postgres_SGroupID)
# print(django_SGroupID)

# print("Atualizando regras")
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 22)
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 5432)
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 8080)
updateSecurityGroupRules(ec2_e2, 'sgManu2' , 80)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 22)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 5432)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 8080)
updateSecurityGroupRules(ec2_e1, 'sgManu1' , 80)

# Getting ubuntu_20 AMI id 
AMI_ID_ubuntu_20_e1 = (getAMIid(ec2_e1, ubuntu18_AMI))
AMI_ID_ubuntu_20_e2 = (getAMIid(ec2_e2, ubuntu18_AMI))

print(Color.F_LightMagenta,"POSTGRES",Color.F_Default)
# Creating an instance 
postgres_instanceId = createInstance(AMI_ID_ubuntu_20_e2, ec2_e2, 'PostgresManu ', 'sgManu2', postgres_script)
waiterInstance(ec2_e2, postgres_instanceId)
PublicIpAddress = getPublicIpAddress(ec2_e2, postgres_instanceId)
print("Postgres PublicIpAddress {}".format(PublicIpAddress))

print(Color.F_LightMagenta,"DJANGO",Color.F_Default)
django_script = (django_script(PublicIpAddress))

django_instanceId = createInstance(AMI_ID_ubuntu_20_e1, ec2_e1, 'DjangoManu ', 'sgManu1', django_script)
waiterInstance(ec2_e1, django_instanceId)

# Creating load balancer
dnsName = createLoadBalancer(elb_e1, 'lbManu', 8080, 8080, subnets_e1, django_SGroupID )
createAutoScaling(as_e1, 'AutoScalingManu', django_instanceId, 'lbManu')

# print("Load Balancer DNS: {}".format(dnsName))
print(Color.F_LightCyan,"Load Balancer DNS: {}".format(dnsName),Color.F_Default)

print(Color.F_LightCyan,"http://{}:8080/admin/".format(dnsName),Color.F_Default)

print(Color.F_LightCyan,"http://{}:8080/tasks/ to see all the tasks".format(dnsName),Color.F_Default)



print(Color.F_White,"__________FIM__________",Color.F_Default)



f = open("lbdns.txt", "w")
f.write("http://{}:8080/".format(dnsName))
f.close()
