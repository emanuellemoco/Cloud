postgres_script = """#!/bin/bash
cd /home/ubuntu

echo "--- Updating server..."
sudo apt update -y

echo "--- Installing Postgre"
sudo apt install postgresql postgresql-contrib -y

echo "--- Creating user cloud"
sudo su - postgres -c "psql -c \\"CREATE USER cloud  WITH PASSWORD 'cloud' \\" "

echo "--- Creating db cloud task"
sudo su - postgres -c "createdb -O cloud tasks"

echo "--- Exposing the service"
sudo sed -i "\\$alisten_addresses = '*' " /etc/postgresql/10/main/postgresql.conf

sudo sed  "\\$ahost    all             all             0.0.0.0/0             trust" /etc/postgresql/10/main/pg_hba.conf > pg_hba.conf
sudo mv pg_hba.conf  /etc/postgresql/10/main/

echo "Firewall"
sudo ufw allow 5432/tcp 

echo "restart"
sudo systemctl restart postgresql

"""

def django_script(ip):

    return ( """#!/bin/bash

    echo "--- Updating server..."
    sudo apt update -y
    sudo apt install python3-pip -y

    cd /home/ubuntu

    echo "--- Cloning "
    git clone https://github.com/emanuellemoco/tasks
    cd tasks/portfolio

    sed -i 's/node1/{0}/g' settings.py 

    cd ..
    
    echo "--- Install "
    ./install.sh 

    echo "--- reboot "
    sudo reboot 
    
    """ ).format(ip)


