#!/bin/bash

# If you want to install the CA in another location, 
# replace the dir below and copy the openssl.cnf with
# the dir variable updated (in the openssl.cnf)
DIR=/etc/ssl
CONFIG="$DIR/openssl.cnf"
cd $DIR 2> /dev/null

# Prepare the structure of the filesystem
mkdir newcerts 2> /dev/null
echo '01' > serial
touch index.txt

echo "Creating the CA cert and private key..."
echo
openssl req -new -x509 -extensions v3_ca -keyout private/cakey.pem \
        -out cacert.pem -days 3650 -config $CONFIG
if [ $? != 0 ]
then
    echo
    echo "There was a problem creating the CA"
    exit 1
fi

echo "Creating the genesis2 request certificate and private key..."
echo
openssl req -new -nodes -out reqGenesis2.pem -config $CONFIG
if [ $? != 0 ]
then
    echo
    echo "There was a problem creating the genesis2 request certificate"
    exit 1
fi

echo "Signing the genesis2 request with the CA..."
echo
openssl ca -out genesis2.cert -config $CONFIG -infiles reqGenesis2.pem
if [ $? != 0 ]
then
    echo
    echo "There was a problem signing the certificate"
    exit 1
fi

mv $DIR/genesis2.cert $DIR/privkey.pem /etc/genesis

echo
echo "Add the following lines in /etc/genesis/genesis.conf in the [genesis] section"
echo "    cert_key = /etc/genesis/privkey.pem"
echo "    cert_file = /etc/genesis/genesis2.cert"
echo "DONE"
