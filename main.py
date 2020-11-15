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



ubuntu_AMI_name = 'ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-20200907'


# FAZER UM WAITER PRO SECURITY GROUP


#devemos usar o dry run?????


#Criar o django e sua imagem para o autoscalling

#Criar e configurar o postgress (DB)

#creteInstance
#argumento userdata tem que seer string
#o que passar ele roda na inicializacao (nao precisa de ssh)

# pega uma maquina limpa, tenta o script na mao, linha a linha
# user data nao roda no home, roda no /

# procurar postgress
# como criar usuario sem o prompt 
#https://stackoverflow.com/questions/18715345/how-to-create-a-user-for-postgres-from-the-command-line-for-bash-automation


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
        print("Deletando sg que ja existe")
        response = ec2.delete_security_group(
        GroupName=name
        )
        return createSecurityGroup(ec2_e2, name)

def updateSecurityGroupRules(ec2, groupId):
    response = ec2.authorize_security_group_ingress(
        GroupId=groupId,
        IpPermissions=[
            {
                'FromPort': 8080,
                'IpProtocol': 'tcp',
                'IpRanges': [
                    {
                        'CidrIp': '0.0.0.0/0',
                    },
                ],
                'ToPort': 8080,
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

        # SecurityGroupIds=[
        #     securityGroupID,
        # ],
    )
    return (response["Instances"][0]['InstanceId'])


def terminateInstances(ec2):
    response = ec2.describe_instances()
    for reservation in response["Reservations"]:
        #print(reservation["Instances"])
   
        for intance in reservation["Instances"]:
            if(intance["State"]["Name"] != "terminated"): 
                for tags in intance["Tags"]:
                    if (tags["Key"] == "Creator"):
                        if (tags["Value"] == "manu"):
                            print("Instance terminated")
                            instanceId = (intance["InstanceId"])
                            response = ec2.terminate_instances(InstanceIds=[instanceId])


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
        print("Imagem not found")


def deleteLoadBalancer(elb, name):
    print("Deleting existed LoadBalancer")
    response = elb.delete_load_balancer(LoadBalancerName=name)

def createLoadBalancer(elb, name, instPort, lbPort, subnets, SecurityGroups):
    try:
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
            # SecurityGroups=[
            #     SecurityGroups,
            # ],
            Tags=[
                {
                    'Key': 'Creator',
                    'Value': 'manu'
                },
            ]
        )
    except: 
        print("ja existe")
        deleteLoadBalancer(elb, name)
        createLoadBalancer(elb, name, instPort, lbPort, subnets, SecurityGroups)

def createAutoScaling(auto, name, InstanceId, lbName):
    try:
        response = auto.create_auto_scaling_group(
        AutoScalingGroupName=name,
        InstanceId=InstanceId,
        MinSize=1,
        MaxSize=2,
        # AvailabilityZones=[
        #     'string',
        # ],
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
        print("ja existe")
        deleteAutoScaling(auto, name)
        print("aa")
        createAutoScaling(auto, name, InstanceId, lbName)
        print("bb")


def deleteAutoScaling(auto, name):
    print("deletando")
    response = auto.delete_auto_scaling_group(
        AutoScalingGroupName=name, ForceDelete=True)
    response = auto.delete_launch_configuration(
        LaunchConfigurationName=name)




def waiterInstance(ec2, instanceId):
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instanceId])

#Nao funcionaaa e nem o waiter do autoscalling
def waiterSecurityGroup(ec2, groupId):
    waiter = ec2.get_waiter('security_group_exists')
    waiter.wait(GroupIds=[groupId])

def waiterImage(ec2, imageId):
    waiter = ec2.get_waiter('image_available')
    waiter.wait(ImageIds=[imageId])




# _________________________________TESTE INSTANCIAS________________________
# # Terminate all my instances
# terminateInstances(ec2_e1)

# # Getting ubuntu_20 AMI id 
# AMI_ID_ubuntu_20 = (getAMIid(ec2_e1, ubuntu_AMI_name))

# # # Creating a Security Group
# securityGroupID = (createSecurityGroup(ec2_e1, 'securityGroupManu'))
# time.sleep(6)

# # Creating an instance 
# instanceId = createInstance(AMI_ID_ubuntu_20, ec2_e1, 'manuP ', 'sg', postgres_script)
# waiterInstance(ec2_e1, instanceId)


# # Update the Security Group Rules
# updateSecurityGroupRules(ec2_e1, securityGroupID)

# # Creating image from an Instance
# ImageIdTESTE = createImage(ec2_e1, instanceId, 'IMAGEMmanu' )

# # time.sleep(10)
# waiterImage(ec2_e1, ImageIdTESTE) 


# #cria uam instancia com essa imagem
# createInstance(ImageIdTESTE, ec2_e1, 'outra ', securityGroupID)

print("INICIO")

# Creating load balancer
# createLoadBalancer(elb_e1, 'lbManu', 80, 90, subnets_e1, 'sg' )

# createAutoScaling(as_e1, 'AutoScalingManu', 'i-09572702c08b20285', 'lbManu')

# createAutoScaling(as_e1, 'AutoScalingManu', instanceId, 'lbManu')



# _________________________________________________________________________



# print("FIM DOS TESTES")
# terminateInstances(ec2_e1)
# deleteAutoScaling(as_e1, 'AutoScalingManu') #da erro se nao existe mas tudo bem (nao vou usar isso)
# deleteLoadBalancer(elb_e1, 'lbManu')


print("FIM TESTE")
