postgres_script = """#!/bin/bash
echo "--- Updating server..."
sudo apt update -y

echo "--- Installing Postgre"
sudo apt install postgresql postgresql-contrib -y

echo "--- Creating user cloud"
sudo su - postgres -c "psql -c \"CREATE USER cloud  WITH PASSWORD 'cloud' \""

echo "--- Creating db cloud task"
sudo su - postgres -c "createdb -O cloud tasks"

echo "--- Exposing the service"
sudo sed -i "\$alisten_addresses = '*' " /etc/postgresql/10/main/postgresql.conf




sudo sed -i "\$ahost all all 192.168.0.0/20 trus " /etc/postgresql/10/main/pg_hba.conf

                                     



"""


– nano /etc/postgresql/10/main/pg_hba.conf 
– Adicione a linha que libera qualquer máquina dentro da subnet do kit: 

host all all 192.168.0.0/20 trust 