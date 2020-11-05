import sys
import boto3


ec2_e1 = boto3.client('ec2', region_name='us-east-1')
ec2_e2 = boto3.client('ec2', region_name='us-east-2')

AMI_ID_ubuntu_20 = 'ami-0dba2cb6798deb6d8'

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
        print("Security Group criado")
        return(security_group['GroupId'])
    except:
        print("Security Group já existe")
        print("Deletando Security Group")
        response = ec2.delete_security_group(
        GroupName=name
        )
        createSecurityGroup(ec2_e2, 'securityGroupManu2')

    


createSecurityGroup(ec2_e2, 'securityGroupManu2')



ubuntu_AMI_name = 'ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-20200907'

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

#print(getAMIid(ec2_e2, ubuntu_AMI_name))





def createInstance(ami_id, ec2):
    print("Criando instância")

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
                        'Value': 'nomeTeste'
                    },
                    {
                        'Key': 'Creator',
                        'Value': 'manu'
                    },
                ]
            },
        ],
    )

#createInstance(AMI_ID_ubuntu_20, ec2_e1)
