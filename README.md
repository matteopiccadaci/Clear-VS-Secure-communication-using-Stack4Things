# Clear versus Secure communication using Stack4Things
## Introduction
This repoository contains a comparative analysis of the communication using cryptographic protocols in Stack4Things against the clear communication.
The scenario is determining how the performance of the communication is affected in the Industrial Internet of Things (IIoT) field, where the device aren't able to use a lot of resources, such as memory and processing power.
In order for the infrastructure to work properly, every communication is performed using the Web of Things (WoT) concept, using an middleware like Crossbar to enable the WAMP (Web Application Messaging Protocol) communication, thus providing the ability to use RPCs (Remote Procedure Calls).
## Implementation
The implementation of the communication is done using the Stack4Things framework, which provides a set of tools to create and manage WoT devices. The devices are implemented using Python and the Crossbar.io framework, which allows for easy integration with WAMP.
This implementation is a derivation of the Stack4Things framework, found in this repository: <a href="https://github.com/MDSLab/Stack4Things_DockerCompose_deployment">Stack4Things_DockerCompose_deployment</a>.
Some modification were made to the original Docker compose file, in order to add the necessary components for the communication.
In particular, the following components were added:
- An **InfluxDB** container, to store the data collected from the devices.
- A **Python Slim** conatiner, whose purpose is exposing a web server which provides some **HATEOAS** (Hypermedia as the Engine of Application State) endpoints to interact with the devices.
- Three **Lightning Rod** containers, which are used to simulate the devices.
- Some **scripts** used to deploy the containers correctly.
In the next sections, the implementation of the communication will be described in detail, focusing on the differences between the clear and secure communication.
The imagined scenario is composed by:
- An **HATEOAS** web server, which can be used to interact with the devices.
- Three **Lightning Rod** devices named **Servers**, which expose three differents RPCs:
    - **get_data**: which simply returns a mesurament values.
    - **clear_write_to_db**: which generates a mesurament value which will be passed in clear to the **Gateway** board.
    - **secure_write_to_db**: which generates a mesurament value, encrypts it and pass it to the **Gateway** board.
- One last **Lightning Rod** device named **Gateway**, which exposes two RPCs.
    - **clear_write_to_db**: which receives the mesurament value in clear and writes it to the InfluxDB database.
    - **secure_write_to_db**: which receives the mesurament value encrypted, decrypts it and writes it to the InfluxDB database.
### HATEOAS
The HATEOAS web server is implemented using Flask, a lightweight web framework for Python. It provides a set of endpoints to interact with the devices and perform operations such as retrieving data and writing to the database.
The choice of using **Hypermedia as the Engine of Application State** (HATEOAS) is to provide a more flexible and dynamic way to interact with the devices: its use let the clients to know nothing about the infrastructure prior to the interaction, which is a pro for the IIoT field, where the devices are often resource-constrained and may not have the ability to store a lot of information about the infrastructure. The use of HATEOAS allows also the server devices to evolve how they work without breaking the clients, as the clients can discover the available operations dynamically.
When a clients connects to the HATEOAS web server, it receives the following JSON response:
```json
{
  "boards": "Board_2_SRV, Board_3_SRV, Board_4_SRV",
  "_links": {
    "self": {
      "href": "/iotronic/boards/"
    },
    "Board_2_SRV": {
      "href": "/iotronic/boards/Board_2_SRV"
    },
    "Board_3_SRV": {
      "href": "/iotronic/boards/Board_3_SRV"
    },
    "Board_4_SRV": {
      "href": "/iotronic/boards/Board_4_SRV"
    }
  }
}
```
From this response, the client can discover the available boards and their respective endpoints. The client can then interact with each board by sending requests to the corresponding endpoints. Let's suppose the client wants to interact with the **Board_2_SRV** board, it can send a request to the endpoint `/iotronic/boards/Board_2_SRV`, which will return the following JSON response:
```json
{
  "board": "Board_2_SRV",
  "_links": {
    "self": {
      "href": "/iotronic/boards/Board_2_SRV"
    },
    "get_data": {
      "href": "/iotronic/boards/Board_2_SRV/get_data"
    },
    "clear_write_to_db": {
      "href": "/iotronic/boards/Board_2_SRV/clear_write_to_db"
    },
    "secure_write_to_db": {
      "href": "/iotronic/boards/Board_2_SRV/secure_write_to_db"
    }
  }
}
```
Now the client can interact with the **Board_2_SRV** board by sending requests to the endpoints, thus invoking ant of the available RPCs.
Let's suppose the client wants to invoke the **secure_write_to_db** RPC: it can send a request to the endpoint `/iotronic/boards/Board_2_SRV/secure_write_to_db`, which will return the following JSON response:
```json
{
  "board": "Board_2_SRV",
  "data": "997",
  "_links": {
    "self": {
      "href": "/iotronic/boards/Board_2_SRV"
    },
    "get_data": {
      "href": "/iotronic/boards/Board_2_SRV/get_data"
    },
    "clear_write_to_db": {
      "href": "/iotronic/boards/Board_2_SRV/clear_write_to_db"
    }
  }
}
```
The user can now perform another request by requesting the same page is now in or it can request any other operation available in the current page.
This approach let the communication to flow easily whether the client is a human or a machine, as the client can discover the available operations dynamically.
### Security
The security of the communication is provided by the use of **Asymmetric** and **Symmetric** cryptographic protocols, along with the use of **Hasing** algorithms to provide integrity.
Given the limited resources of the devices, the communication is designed to be as lightweight as possible, while still providing a good level of security. 
The algorithms used are:
- **Asymmetric**: RSA (Rivest-Shamir-Adleman) algorithm 
- **Symmetric**: AES-ECB (Advanced Encryption Standard Electronic Codebook) algorithm 
- **Hashing**: SHA-256 (Secure Hash Algorithm 256 bits) algorithm

After the data is generated, an *msg* variable is created, which contains the data to be sent to the **Gateway** device. The data digest is then calculated using the SHA-256 algorithm, which provides integrity to the data. Then, a *random symmetric key* is genrated and use to encypt the *msg* variable using the AES-ECB algorithm. In the end, the *random key* and the *msg hash* are encrypted using the RSA algorithm: in particular, the first is encrypted using the **Public Key** of the **Gateway** whereas the second is **Signed** using the **Server's** private key. This approach provides confidentiality, integrity and authenticity to the data.
The **Gateway**, upon receiving the data, decrypts the *random key* using its **Private Key** and then uses it to decrypt the *msg* variable. The digest of the *msg* variable is then calculated and compared with the decrypted hash: if they match, the data is considered valid and is written to the InfluxDB database.
### WAMP_SRV and WAMP_GT plugins
The **Stack4Things** framework provides the ability to store plugins and inject them into the devices when needed. In the above section it is showed the configuration of the *Lightning Rod* devices: the implementation of the plugins in **S4T** let the developer to change the behavior of each machine by simply injecting and calling the desired plugin (of course, some operations like checking if all the requirements are met, such as the presence of the required libraries, are performed before injecting the plugin).
In this case, the **WAMP_SRV** and **WAMP_GT** plugins are injected into the **Lightning Rod** devices, which provide the ability to communicate using WAMP. The **WAMP_SRV** plugin is used by the **Servers** devices, while the **WAMP_GT** plugin is used by the **Gateway** device.
#### WAMP_SRV plugin
The **WAMP_SRV** plugin is used by the **Servers** devices to expose the RPCs and interact with the **Gateway** device. The plugin provides the above mentioned RPCs to interact with the **Gateway** device. After the response is given by the **Gateway**, the **Servers** devices can then return the response to the client.
The devices which execute the **WAMP_SRV** plugin are not able to interact with the InfluxDB database directly: this is a security feature which will be later discussed.
Here follows a snippet of the **WAMP_SRV** plugin:
```python
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
                    '''...'''

                async def clear_write_to_db():
                    '''...'''
                async def secure_write_to_db():
                    '''...'''

                await session.register(get_data, f"iotronic.{board_name}.get_data")
                await session.register(clear_write_to_db, f"iotronic.{board_name}.clear_write_to_db")
                await session.register(secure_write_to_db, f"iotronic.{board_name}.secure_write_to_db")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(component.start(loop=loop))

        threading.Thread(target=start_wamp, name="***", daemon=True).start()
        LOG.info("[WAMP] *** working, waiting for RPC..")
```
The *def_run* method is the entrypoint of the plugin: the **Lightning Rod** interface expects this method to be called in order to start the plugin. The method creates a new thread which starts the WAMP component, which is responsible for handling the WAMP communication. The component registers the RPCs and waits for incoming requests. When a request is received, the corresponding RPC is invoked and the response is returned to the client.
The RPCs are registered using the `session.register` method, which takes the RPC function and the name of the RPC as arguments. The RPCs are then available to be invoked by the client.
#### WAMP_GT plugin
The **WAMP_GT** plugin is used by the **Gateway** device to interact with the **Servers** devices and the InfluxDB database. The plugin provides the two RPCs to write data to the database, both in clear and secure mode.
The **Gateway** device is the only one able to interact with the InfluxDB database, thus providing a single point of access to the database. The board which execute the **WAMP_GT** plugin are seen as crucial and delicate, as they are the only ones able to interact with the database and perform the necessary operations to store the data. This is the reason why the client cannot interact with the **Gateway** boards via the HATEOAS web server. As for the implementation of the plugin, it is similar to the **WAMP_SRV** plugin, with the different behavior of the RPCs.
## Performance
In order to evaluate the performance of the communication, a set of tests were performed using the **Servers** devices and the **Gateway** device. The tests were performed in two different scenarios: one using clear communication and the other using secure communication.
The *benchmark.py* script is used to perform the tests, which can be found in the repository. The script performs the following operations:
- Connects to the HATEOAS web server and retrieves the available boards.
- For each board, it invokes the **clear_write_to_db** RPC to write data to the database in clear mode and measures the elapsed time between the request invocation and its termination.
- For each board, it invokes the **secure_write_to_db** RPC to write data to the database in secure mode and measures the elapsed time between the request invocation and its termination.
For a request to be sent, the previous must be completed.
Here follow the graphical representation of the results obtained from the tests:

<img src="images/Clear Communication.png" alt="Clear communication" width="750"/>
<img src="images/Secure communication.png" alt="Secure Communication" width="750"/>

It is clear that the secure communication is slower than the clear communication, as expected. The difference in performance is due to the overhead introduced by the cryptographic operations, such as encryption and decryption, which are necessary to provide security to the communication.
The maximum time taken to perform a request in clear mode is around 0.2 seconds, while the maximum time taken to perform a request in secure mode is around 22 seconds. 
The mean time taken for the clear communication is around 0.1 seconds, while the mean time taken for the secure communication is around 13 seconds.
The standard deviation for both the types of communication is quite high, as the time taken to perform a request can vary significantly depending on the load of the system and the network conditions.
This makes the clear communication more suitable for scenarios where low latency is required, while the secure communication is more suitable for scenarios where security is a priority and the overhead introduced by the cryptographic operations is acceptable.
## Conclusion
The use of HATEOAS provides a flexible and dynamic way to interact with the devices, allowing clients to discover available operations dynamically.
The security of the communication is provided by the use of asymmetric and symmetric cryptographic protocols, along with hashing algorithms to provide integrity. The performance tests show that the secure communication is slower than the clear communication, as expected, due to the overhead introduced by the cryptographic operations.
The plugin feature of the Stack4Things framework allows for easy integration of WAMP communication, which is used to expose RPCs and interact with the devices.
The overall implementation let the developer to have a rapid and dynamic infrastructure to change and evolve the devices behavior, along with the possibility to switch any device logic on the fly.

# Video Demo
https://github.com/user-attachments/assets/c8e737bf-fa82-4989-abbc-d86da6e0bad5


## Troubleshooting and known limitations
- On Windows and Linux machines the "iotronic-conductor" and "iotronic-wagent" may not start automatically. They can be manually started using Docker Desktop or using the command ```docker start iotronic-conductor``` and ```docker start iotronic-wagent```.
- Due to limitations imposed by the manufacturer, on Mac machines the DNS system is avaiable only when interacting via containers (for example, if you visit the http://hateoas_server:4053 page on a web browser, the connection cannot be established. In this case, you should use 0.0.0.0:4053). The same goes for Linux, which would require a modification to the ```/etc/hosts``` file. On Windows machines, the DNS resolver works without any modification.
- The Plugin call on any board often results very slow and a pop-up with an error is shown: despite this, the plugins are correctly called (you can check by reading the board's logs).


