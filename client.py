#!/usr/bin/env python

import sys 
import requests
from color import *

f = open("lbdns.txt", "r")
dnsName = f.readline()
f.close()


def get_task():
    try:
        r = requests.get('{}tasks'.format(dnsName))
        print(r.json())
    except:
        print(Color.F_LightYellow,"Servidor sem resposta.",Color.F_Default)
    
    
def post_task():
    try:
        url = "{}tasks/post".format(dnsName)
        fields = {'title': sys.argv[2], 'pub_date': sys.argv[3], 'description': sys.argv[4]}
        r = requests.post(url, data = fields)
        if (r.status_code == 201):
            print(Color.F_LightGreen,"Tarefa adicionada com sucesso!",Color.F_Default)
        else:
            print(Color.F_LightYellow,"Servidor sem resposta.",Color.F_Default)
    except:
        print(Color.F_LightYellow,"Servidor sem resposta.",Color.F_Default)

    

if sys.argv[1] == 'get':
    get_task()
elif sys.argv[1] == 'post':
    post_task()
else:
    print("Comando nao valido")




## 2020-11-09T00:00:00Z