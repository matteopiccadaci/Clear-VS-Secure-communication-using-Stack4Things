#!/bin/bash
set -e

echo "[INFO] Installazione di OpenSSL..."
apt-get update && apt-get install -y openssl

echo "[INFO] Generazione della Root CA..."
mkdir -p /etc/ssl/iotronic
cd /etc/ssl/iotronic

openssl genrsa -out iotronic_CA.key 2048
openssl req -x509 -new -nodes -key iotronic_CA.key -sha256 -days 18250 \
  -subj "/C=IT/O=iotronic" -out iotronic_CA.pem

echo "[INFO] Generazione della chiave privata e del certificato per Crossbar..."
openssl genrsa -out crossbar.key 2048
openssl req -new -key crossbar.key -subj "/C=IT/O=iotronic/CN=crossbar" -out crossbar.csr
openssl x509 -req -in crossbar.csr -CA iotronic_CA.pem -CAkey iotronic_CA.key -CAcreateserial -out crossbar.pem -days 18250 -sha256

for NODE in Board_1_GT Board_2_SRV Board_3_SRV Board_4_SRV; do
  echo "[INFO] Generazione certificati per $NODE..."
  mkdir -p /etc/ssl/iotronic/$NODE
  cd /etc/ssl/iotronic/$NODE

  openssl genrsa -out $NODE.key.pem 2048
  openssl rsa -in $NODE.key.pem -pubout -out $NODE.pub.pem
  openssl req -new -key $NODE.key.pem \
    -subj "/C=IT/O=Iotronic/OU=Nodes/CN=$NODE" \
    -out $NODE.csr.pem

  openssl x509 -req -in $NODE.csr.pem \
    -CA ../iotronic_CA.pem \
    -CAkey ../iotronic_CA.key \
    -CAcreateserial \
    -out $NODE.cert.pem \
    -days 365 \
    -sha256
  
  if [ "$NODE" != "Board_1_GT" ]; then
  cp $NODE.pub.pem /etc/ssl/iotronic/Board_1_GT/
  fi
  
done


for NODE in Board_2_SRV Board_3_SRV Board_4_SRV; do
  cp /etc/ssl/iotronic/Board_1_GT/Board_1_GT.pub.pem /etc/ssl/iotronic/$NODE/
done

for NODE in Board_1_GT Board_2_SRV Board_3_SRV Board_4_SRV; do
  cp /etc/ssl/iotronic/iotronic_CA.pem /etc/ssl/iotronic/$NODE/
done

# The public keys of the SRV nodes are copied to the GT node
# The public keys of the GT node are copied to the SRV nodes
# The CA certificate is copied to all nodes to enable SSL


echo "[INFO] Impostazione permessi certificati..."
chmod 644 /etc/ssl/iotronic/iotronic_CA.key /etc/ssl/iotronic/iotronic_CA.pem \
  /etc/ssl/iotronic/crossbar.key /etc/ssl/iotronic/crossbar.pem
chmod 755 /etc/ssl/iotronic

echo "[INFO] Certificati generati con successo."

# Mantieni il container attivo
tail -f /dev/null
