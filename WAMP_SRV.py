import asyncio
import json
import base64
import random
import string
import socket
import hashlib
import threading
import time
import ssl
from oslo_log import log as logging
from iotronic_lightningrod.modules.plugins import Plugin
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Util.Padding import pad
from Crypto.Util.number import bytes_to_long
from autobahn.asyncio.component import Component

LOG = logging.getLogger(__name__)
board_name = socket.gethostname()
board_GT_name = "Board_1_GT"

with open(f"/etc/ssl/iotronic/node_certs/{board_name}.key.pem", "rb") as f:
    priv_K_SRV = RSA.import_key(f.read())
with open(f"/etc/ssl/iotronic/node_certs/{board_GT_name}.pub.pem", "rb") as f:
    pub_K_GT = RSA.import_key(f.read())


class Worker(Plugin.Plugin):
    def __init__(self, uuid, name, q_result=None, params=None):
        super(Worker, self).__init__(uuid, name, q_result, params)

    def harvest_data(self):
        return ''.join(str(random.randint(0, 9)) for _ in range(3))

    def random_key(self):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

    def encrypt_msg(self):
        msg = json.dumps({"0": self.harvest_data(), "1": board_name})
        msg_hash = hashlib.sha256(msg.encode('utf-8')).hexdigest()
        LOG.info(f"[WAMP] Message to encrypt: {msg_hash}")
        AES_key = self.random_key()
        cipher = AES.new(AES_key.encode('utf-8'), AES.MODE_ECB)
        enc_msg = cipher.encrypt(pad(msg.encode('utf-8'), AES.block_size))
        cipher_rsa = PKCS1_v1_5.new(pub_K_GT)
        enc_key = cipher_rsa.encrypt(AES_key.encode('utf-8'))
        enc_hash = pow(bytes_to_long(msg_hash.encode('utf-8')), priv_K_SRV.d, priv_K_SRV.n)

        return base64.b64encode(json.dumps({
            "enc_msg": base64.b64encode(enc_msg).decode('utf-8'),
            "enc_key": base64.b64encode(enc_key).decode('utf-8'),
            "enc_hash": base64.b64encode(enc_hash.to_bytes((enc_hash.bit_length() + 7) // 8, 'big')).decode('utf-8')
        }).encode('utf-8')).decode('utf-8')

    def run(self):
        def start_wamp():
            ssl_ctx = ssl._create_unverified_context()

            component = Component(
                transports=[
                    {
                        "type": "websocket",
                        "url": "wss://crossbar:8181/ws",
                        "endpoint": {
                            "type": "tcp",
                            "host": "crossbar",
                            "port": 8181,
                            "tls": ssl_ctx
                        },
                        "serializers": ["json", "msgpack"]
                    }
                ],
                realm="s4t"
            )

            @component.on_join
            async def on_join(session, details):
                LOG.info(f"[WAMP] Session joined as {board_name}")
                LOG.info("[WAMP] RPCs registered: get_data, clear_write_to_db, secure_write_to_db")

                async def get_data():
                    data = self.harvest_data()
                    LOG.info(f"[RPC] get_data -> {data}")
                    return data

                async def clear_write_to_db():
                    msg = json.dumps({"0": self.harvest_data(), "1": board_name})
                    target_rpc = f"iotronic.{board_GT_name}.clear_write_to_db"
                    try:
                        res = await session.call(target_rpc, msg)
                        LOG.info(f"[RPC] Sent clear msg to {target_rpc}")
                        return res
                    except Exception as e:
                        LOG.error(f"Failed to send RPC: {e}")
                        return {"status": "error", "detail": str(e)}

                async def secure_write_to_db():
                    msg = self.encrypt_msg()
                    target_rpc = f"iotronic.{board_GT_name}.secure_write_to_db"
                    try:
                        res = await session.call(target_rpc, msg)
                        LOG.info(f"[RPC] Sent encrypted msg to {target_rpc}")
                        return res
                    except Exception as e:
                        LOG.error(f"Failed to send RPC: {e}")
                        return {"status": "error", "detail": str(e)}

                await session.register(get_data, f"iotronic.{board_name}.get_data")
                await session.register(clear_write_to_db, f"iotronic.{board_name}.clear_write_to_db")
                await session.register(secure_write_to_db, f"iotronic.{board_name}.secure_write_to_db")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(component.start(loop=loop))

        threading.Thread(target=start_wamp, name="WAMP_SRV", daemon=True).start()
        LOG.info("[WAMP] Server working, waiting for RPC..")
