import sys
import boto3
import time

ec2_e1 = boto3.client('ec2', region_name='us-east-1')
ec2_e2 = boto3.client('ec2', region_name='us-east-2')


ubuntu_AMI_name = 'ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-20200907'

#devemos usar o dry run?????


# checar e matar todas as instancias e configuracoes 
# com try e except caso não exista

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
        print("Security Group {} criado".format(name))
        return(security_group['GroupId'])
    except:
        print("Deletando Security Group já existente")
        response = ec2.delete_security_group(
        GroupName=name
        )
        return createSecurityGroup(ec2_e2, name)


def getAMIid(ec2, name):

    response = ec2.describe_images(
        Filters=[
            {
                'Name': 'name',
                'Values': [name]
            },
        ],
    )
    return response['Images'][0]['ImageId']




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
    ### checar se o state é terminated

    response = ec2.describe_instances()
    #print(response["Reservations"][0]["Instances"][0]["InstanceId"])
    for reservation in response["Reservations"]:
        #print(reservation["Instances"])
   
        for intance in reservation["Instances"]:
            #print(intance["State"])
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
    except:
        print("Unregistering existing AMI") 
        imageId= getAMIid(ec2_e1, name)
        response = ec2.deregister_image(ImageId=imageId)
        return createImage(ec2, instanceId, name)



def espera(ec2, instanceId):
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instanceId])





terminateInstances(ec2_e1)

AMI_ID_ubuntu_20 = (getAMIid(ec2_e1, ubuntu_AMI_name))

securityGroupID = (createSecurityGroup(ec2_e1, 'securityGroupManu'))

instanceId = createInstance(AMI_ID_ubuntu_20, ec2_e1, 'OLAR ', securityGroupID)

espera(ec2_e1, instanceId)

createImage(ec2_e1, instanceId, 'IMAGEMMMMMM' )

