import sys
import boto3
import time

ec2_e1 = boto3.client('ec2', region_name='us-east-1')
ec2_e2 = boto3.client('ec2', region_name='us-east-2')

elb_e1 = boto3.client('elbv2', region_name='us-east-1')
elb_e2 = boto3.client('elbv2', region_name='us-east-2')



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




def createInstance(ami_id, ec2, instanceName, securityGroupID):
    print("Criando instância {}".format(instanceName))

    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType='t2.micro',
        MaxCount=1,
        MinCount=1,
        Monitoring={
            'Enabled': True
        },
    
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


def getLoadBalancerArn(elb, name):
    response = elb.describe_load_balancers()
    for lb in response["LoadBalancers"]:
        if (lb["LoadBalancerName"]==name):
            LoadBalancerArn = lb["LoadBalancerArn"]
            deleteLoadBalancer(elb, LoadBalancerArn)


def createLoadBalancer(elb, name, port, subnets, securityGroupID):
    #Check if there is a LB with the same name and delete it 
    getLoadBalancerArn(elb_e1, name)

    response = elb.create_load_balancer(
        Name=name,
        # SecurityGroups=[securityGroupID],
        Tags=[
            {
                'Key': 'Creator',
                'Value': 'manu'
            },
        ],
        Subnets=subnets,
    )
    print("LoadBalancer {} created".format(name))
    return(response["LoadBalancers"][0]["LoadBalancerArn"])


def deleteLoadBalancer(elb, LoadBalancerArn):
    print("Deleting existed LoadBalancer")
    response = elb.delete_load_balancer(LoadBalancerArn=LoadBalancerArn)


#criar e registrar target group

def getVpcId(ec2):
    response = ec2.describe_vpcs()
    for vpc in response["Vpcs"]:
        return vpc["VpcId"]
    
def getTargetGroupArn(elb, name):
    response = elb.describe_target_groups()
    print("___________")
    print(response)
    print("___________")
    for tg in response["TargetGroups"]:
        if (tg["TargetGroupName"]==name):
            print("ja existe")
            TargetGroupArn = tg["TargetGroupArn"]
            deleteTargetGroup(elb, TargetGroupArn)

def createTargetGroup(elb, port, name):
    #Check if the TG already exists and delete it
    getTargetGroupArn(elb, name)

    print("Creating TargetGroup")
    VpcId = getVpcId(ec2_e1)

    response = elb.create_target_group(
    Name=name,
    Protocol='HTTP',
    Port=port,
    VpcId=VpcId,
    TargetType='instance',
    Tags=[
        {
            'Key': 'Creator',
            'Value': 'manuuu'
        },
    ]
)


def deleteTargetGroup(elb, TargetGroupArn):
    print("Deleting existed TargetGroup")
    response = elb.delete_target_group(TargetGroupArn=TargetGroupArn)



createTargetGroup(elb_e1, 8080, 'TargetGroupManu')




def waiterInstance(ec2, instanceId):
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instanceId])

def waiterSecurityGroup(ec2, groupId):
    waiter = ec2.get_waiter('security_group_exists')
    waiter.wait(GroupIds=[groupId])

def waiterImage(ec2, imageId):
    waiter = ec2.get_waiter('image_available')
    waiter.wait(ImageIds=[imageId])


# _________________________________TESTE INSTANCIAS________________________
# # Terminate all instances
# terminateInstances(ec2_e1)

# # Getting ubuntu_20 AMI id 
# AMI_ID_ubuntu_20 = (getAMIid(ec2_e1, ubuntu_AMI_name))

# Creating a Security Group
# securityGroupID = (createSecurityGroup(ec2_e1, 'securityGroupManu'))
# waiterSecurityGroup(ec2_e1, securityGroupID)         
# time.sleep(6)

# # Creating an instance 
# instanceId = createInstance(AMI_ID_ubuntu_20, ec2_e1, 'OLAR ', securityGroupID)
# waiterInstance(ec2_e1, instanceId)

# # Update the Security Group Rules
# updateSecurityGroupRules(ec2_e1, securityGroupID)

# # Creating image from an Instance
# ImageIdTESTE = createImage(ec2_e1, instanceId, 'IMAGEMmanu' )

# # time.sleep(10)
# waiterImage(ec2_e1, ImageIdTESTE) 


# #cria uam instancia com essa imagem
# createInstance(ImageIdTESTE, ec2_e1, 'outra ', securityGroupID)

# Creating load balancer
# loadBalancerArn = createLoadBalancer(elb_e1, 'lbManu', 80, subnets_e1, 'a' ) 

# _________________________________________________________________________




print("FIM TESTE")
