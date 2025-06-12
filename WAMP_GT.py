import asyncio
import json
import base64
import socket
import hashlib
import threading
from datetime import datetime, timezone

import ssl
from oslo_log import log as logging
from iotronic_lightningrod.modules.plugins import Plugin
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Util.number import long_to_bytes, bytes_to_long
from autobahn.asyncio.component import Component
from influxdb_client import InfluxDBClient, Point, WritePrecision

LOG = logging.getLogger(__name__)
board_name = socket.gethostname()

with open(f"/etc/ssl/iotronic/node_certs/{board_name}.key.pem", "rb") as key_file:
    private_key = key_file.read()


def decrypt_aes(ciphertext, key):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted.decode('utf-8')


def decrypt_rsa(ciphertext):
    rsa_key = RSA.import_key(private_key)
    cipher = PKCS1_v1_5.new(rsa_key)
    decrypted = cipher.decrypt(ciphertext, None)
    return decrypted.decode('utf-8')


def decrypt_and_verify_message(message):
    decoded_payload = json.loads(base64.b64decode(message))
    aes_key = decrypt_rsa(base64.b64decode(decoded_payload['enc_key']))
    decrypted_msg = decrypt_aes(base64.b64decode(decoded_payload['enc_msg']), aes_key)
    board_name = json.loads(decrypted_msg)["1"]
    with open(f"/etc/ssl/iotronic/node_certs/{board_name}.pub.pem", "rb") as f:
        pub_key = RSA.import_key(f.read())
    decrypted_hash = long_to_bytes(
        pow(bytes_to_long(base64.b64decode(decoded_payload['enc_hash'])), pub_key.e, pub_key.n)
    )
    computed_hash = hashlib.sha256(decrypted_msg.encode('utf-8')).hexdigest()
    if decrypted_hash.decode('utf-8') != computed_hash:
        LOG.error("Hash mismatch: message integrity compromised")
        return
    return decrypted_msg


def store_to_db(write_api, bucket, org, data):
    m = json.loads(data)
    point = (
        Point("value")
        .tag("board", str(m['1']))
        .field("value", float(m['0']))
        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )
    write_api.write(bucket=bucket, org=org, record=point)


class Worker(Plugin.Plugin):
    def __init__(self, uuid, name, q_result=None, params=None):
        super(Worker, self).__init__(uuid, name, q_result, params)

    def run(self):
        board_name = socket.gethostname()
        token = "hasuighduisaghaduigcui"
        org = "S4T"
        bucketSec = "secure_communication"
        bucketClr = "clear_communication"

        client = InfluxDBClient(
            url="http://influxdb:8086",
            token=token,
            org=org
        )

        def start_wamp():
            async def wamp_main():
                component = Component(
                    transports=[
                        {
                            "type": "websocket",
                            "url": "wss://crossbar:8181/ws",
                            "endpoint": {
                                "type": "tcp",
                                "host": "crossbar",
                                "port": 8181,
                                "tls": ssl._create_unverified_context()
                            },
                            "serializers": ["json", "msgpack"]
                        }
                    ],
                    realm="s4t"
                )

                @component.on_join
                async def on_join(session, details):
                    LOG.info(f"[WAMP] Session joined as {board_name}")
                    LOG.info("[WAMP] RPCs registered: clear_write_to_db, secure_write_to_db")

                    async def clear_write_to_db(*args, **kwargs):
                        LOG.info(f"[RPC] clear_write_to_db called with data: {args[0]}")
                        data = args[0]
                        store_to_db(client.write_api(), bucketClr, org, data)
                        return data

                    async def secure_write_to_db(*args, **kwargs):
                        LOG.info(f"[RPC] secure_write_to_db called with data: {args[0]}")
                        data = decrypt_and_verify_message(args[0])
                        store_to_db(client.write_api(), bucketSec, org, data)
                        return data

                    await session.register(clear_write_to_db, f"iotronic.{board_name}.clear_write_to_db")
                    await session.register(secure_write_to_db, f"iotronic.{board_name}.secure_write_to_db")

                await component.start()

            while True:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(wamp_main())
                except Exception as e:
                    LOG.error(f"[WAMP] Error in WAMP loop: {e}")
                finally:
                    asyncio.set_event_loop(None)

        threading.Thread(target=start_wamp, name="WAMP_GT", daemon=True).start()
        LOG.info("[WAMP] Gateway working, waiting for RPC...")

#ssl_context = ssl.create_default_context(cafile="/etc/ssl/iotronic/node_certs/iotronic_CA.pem")