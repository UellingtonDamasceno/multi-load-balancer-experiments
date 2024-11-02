from fogledgerIota.iota.IotaBasic import (IotaBasic)
from fogledgerIota.iota.config.NodeConfig import (NodeConfig)
from fogledgerIota.iota.config.CoordConfig import (CoordConfig)
from fogledgerIota.iota.config.SpammerConfig import (SpammerConfig)
from fogledgerIota.iota.config.ApiConfig import (ApiConfig)
from fogledgerIota.iota.config.WebAppConfig import (WebAppConfig)
from typing import List
from fogbed import (
    VirtualInstance, setLogLevel, FogbedDistributedExperiment, Worker, Container, Controller,
    HardwareResources, Resources
)
import signal
from datetime import datetime, timedelta
import time


setLogLevel('info')

# MACHINES DEFINITION
MIOTA1 = 'larsid02'
MIOTA2 = 'larsid03'
MCONNECTOR = 'larsid04'

MGATEWAYS = ['larsid05', 'larsid10', 'larsid08', 'larsid09']

MDEVICES = ['larsid14', 'larsid11', 'larsid12', 'larsid13']


# EXPERIMENTS CONFIGURATION
EXP_NUM = '0'
EXP_TYPE = '0'
EXP_LEVEL = '0'
API_URL = 'http://larsid23:8080/api/latency-records/records'

MAX_QTD_DEVICE_PER_GATEWAYS = [32,32,0,0]
QTD_MAX_DEVICES = sum(MAX_QTD_DEVICE_PER_GATEWAYS)
QTD_DEVICES_PER_MACHINE = QTD_MAX_DEVICES // len(MAX_QTD_DEVICE_PER_GATEWAYS)
LOAD_LIMIT = '16'
MAX_QTD_GATEWAYS = len(MAX_QTD_DEVICE_PER_GATEWAYS)

IS_BALANCEABLE = '0'
IS_MULTI_LAYER = '0'

# DEVICES CONFIGURATION
COLLECT_TIME = '100'
PUBLISH_TIME = '1000'
SAMPLING_INTERVAL = '1000'
LB_ENTRY_TIMEOUT = '10'
TIMEOUT_LB_REPLY = '10'
TIMEOUT_GATEWAY = '10'
BUFFER_SIZE = '64'

# GATEWAY CONFIGURATION
DEBUG_MODE_VALUE = 'true'
INDEXES = 'LB_*'
UP_DLT_URL = ''
UP_ZMQ_SOCKET_URL = ''
DU_DLT_URL = ''
DU_ZMQ_SOCKET_URL = ''

UP_DLT_PORT = DU_DLT_PORT = '14265'
UP_ZMQ_SOCKET_PORT = DU_ZMQ_SOCKET_PORT = '5556'

class IPGen:
    current = 1 

    @staticmethod
    def next_ip():
        if IPGen.current > 256:
            raise StopIteration("Todos os IPs válidos foram gerados.")
        ip = f"172.17.0.{IPGen.current}"
        IPGen.current += 1
        return ip

def conStr(container: Container) -> str:
    env_str = ', '.join(f"{key}: {value}" for key, value in container.environment.items())
    port_bindings_str = ', '.join(f"{host_port} -> {container.bindings[host_port]}" for host_port in container.bindings)

    return (f"Name: {container.name}, "
            f"IP: {container.ip if container.ip else 'N/A'}, "
            f"Port: {{{port_bindings_str}}}, "
            f"Env: {{{env_str}}}, "
            f"Resources: {container.resources}")

def createFotDevice(name: str, ip: str,  config: dict):
    device = Container(
        name=name,
        dcmd='java -jar device.jar',
 #       ip=ip,
        dimage='udamasceno/virtual-fot-device:latest',
        environment={
            'DEVICE_ID': name,
            'BROKER_IP': config['broker_ip'],
            'PORT': config['port'], 
            'USERNAME':config['username'],
            'PASSWORD': config['password'],
            'EXP_NUM': config['exp_num'],
            'EXP_TYPE': config['exp_type'],
            'EXP_LEVEL': config['exp_level'],
            'API_URL': config['api_url'],
            'BUFFER_SIZE': config['buffer_size']
        },
        resources=HardwareResources(16.0, 4096)
    )
    print(conStr(device))
    return device

def createFotGatway(name: str, ip: str,  config: dict, mqtt_port: str = '1883'):
    gateway = Container(
        name=name,
  #      ip=ip,
#        dimage='larsid/load-balancer:latest',
        dcmd='/bin/bash ./usr/local/bin/karaf-init.sh',
        dimage='udamasceno/mlb:latest', 
        environment={
            'DEBUG_MODE_VALUE': DEBUG_MODE_VALUE,
            'DLT_URL': config['dlt_url'],
            'DLT_PORT': config['dlt_port'],
            'ZMQ_SOCKET_URL': config['zmq_socket_url'],
            'ZMQ_SOCKET_PORT': config['zmq_socket_port'],
            'SAMPLING_INTERVAL': config['sampling_interval'],
            'LOAD_LIMIT': config['load_limit'],
            'LB_ENTRY_TIMEOUT': config['lb_entry_timeout'],
            'TIMEOUT_LB_REPLY': config['timeout_lb_reply'],
            'TIMEOUT_GATEWAY': config['timeout_gateway'],
            'COLLECT_TIME': config['collect_time'],
            'PUBLISH_TIME': config['publish_time'],
            'GROUP': config['group'],
            'IS_BALANCEABLE': config['is_balanceable'],
            'IS_MULTI_LAYER': config['is_multi_layer'],
            'GATEWAY_PORT': mqtt_port
        },
        port_bindings={'8081': '8081', '14265': '14265', '1883': mqtt_port},
        resources=HardwareResources(cu=12.0, mu=8192)
    )
    print(conStr(gateway))
    return gateway

def create_connector():
    hornet_connector = Container(
        name='connector',
        dcmd='java -jar hornet-connector.jar',
        dimage='udamasceno/hornet-connector:latest',
        environment={
            'DEBUG_MODE_VALUE': DEBUG_MODE_VALUE,
            'UD_DLT_URL': UP_DLT_URL,
            'UD_DLT_PORT': UP_DLT_PORT,
            'UD_ZMQ_URL': UP_ZMQ_SOCKET_URL,
            'UD_ZMQ_PORT': UP_ZMQ_SOCKET_PORT,
            'DU_DLT_URL': DU_DLT_URL,
            'DU_DLT_PORT': DU_DLT_PORT,
            'DU_ZMQ_URL': DU_ZMQ_SOCKET_URL,
            'DU_ZMQ_PORT': DU_ZMQ_SOCKET_PORT,
        },
        resources=HardwareResources(cu=12.0, mu=8192)
    )
    print(conStr(hornet_connector))
    return hornet_connector

def create_zmq_bridge(iota_ip: str, zmq_ip: str, suffix:str, indexes: str, port: str = '5556'):
    zmq = Container(
        name=f'zmq-{suffix}',
    #    ip=zmq_ip,
        dimage='larsid/iota-zmq-bridge:1.0.0',
        dcmd=f'/entrypoint.sh',
        port_bindings={'5556': port},
        environment={
            'MQTT_IP': iota_ip,
            'INDEXES': indexes,
            'NUM_WORKERS': 20
        },
        resources=HardwareResources(12.0, 8192)
    )
    print(conStr(zmq))
    return zmq

setLogLevel('info')

if (__name__ == '__main__'):

    controller = Controller('localhost', 6633)

    print(controller)
#    exp = FogbedDistributedExperiment(
#        max_cpu=16,
#        max_memory=12288,
#        controller_ip=controller.ip,
#        controller_port=controller.port)
    exp = FogbedDistributedExperiment()

### IOTA1 CONFIGURATION
    iota1_nodes = [
    NodeConfig(
        name=f'i1-node{i}',
#        ip=IPGen.next_ip(),
        port_bindings={
            '8081': str(808 + i),
            '14256': str(1426 + i),
            '1883': str(188 + i)
        }
    )
    for i in range(4)
    ]

    iota1_virtual = exp.add_virtual_instance('iota1')
    iota1 = IotaBasic(exp=exp, prefix='iota1', virtual_instance=iota1_virtual, conf_nodes=iota1_nodes)
    node1 = iota1.containers['i1-node0']
    node1.resources = HardwareResources(cu=12.0, mu=8192) 
    UP_DLT_URL = node1.ip
    print(conStr(node1))

    zmq1_bridge = create_zmq_bridge(UP_DLT_URL, IPGen.next_ip(),  'i1', INDEXES, UP_ZMQ_SOCKET_PORT)
    UP_ZMQ_SOCKET_URL = zmq1_bridge.ip
    exp.add_docker(zmq1_bridge, iota1_virtual)

    iota1_worker = exp.add_worker(MIOTA1)
    iota1_worker.add(iota1_virtual, reachable=True)

### IOTA2 CONFIGURATION
    iota2_nodes = [
    NodeConfig(
        name=f'i2-node{i}',
   #     ip=IPGen.next_ip(),
        port_bindings={
            '8081': str(808 + i),
            '14265': str(1426 + i),
            '1883': str(188 + i)
        }
    )
    for i in range(4)
    ]
    iota2_virtual = exp.add_virtual_instance('iota2')
    iota2 = IotaBasic(exp=exp, prefix='iota2', virtual_instance=iota2_virtual,  conf_nodes=iota2_nodes)
    node2 = iota2.containers['i2-node0']
    node2.resources = HardwareResources(12.0, 8192)
    DU_DLT_URL = node2.ip
    print(conStr(node2))

    zmq2_bridge = create_zmq_bridge(DU_DLT_URL, IPGen.next_ip(), 'i2', INDEXES, DU_ZMQ_SOCKET_PORT)
    DU_ZMQ_SOCKET_URL = zmq2_bridge.ip
    exp.add_docker(zmq2_bridge, iota2_virtual)

    iota2_worker = exp.add_worker(MIOTA2)
    iota2_worker.add(iota2_virtual, reachable=True)


### CONNECTOR CONFIGURATION 

    connector = create_connector()

    connector_virtual = exp.add_virtual_instance('connector')
    exp.add_docker(connector, connector_virtual)
    connector_worker = exp.add_worker(MCONNECTOR)
    connector_worker.add(connector_virtual, reachable=True)
 
### GATEWAYS CONFIGURATION
    gateways = []
    gateways_virtual = []
    gateways_workers = [exp.add_worker(worker) for worker in MGATEWAYS]

    for i in range(MAX_QTD_GATEWAYS):
        dlt_url = UP_DLT_URL if i % 2 == 0 else DU_DLT_URL
        zmq_socket_url = UP_ZMQ_SOCKET_URL if i % 2 == 0 else DU_ZMQ_SOCKET_URL
        gname = f'gateway-{i}'

        gateway = createFotGatway(gname, IPGen.next_ip(), {
                        'dlt_url': dlt_url,
                        'dlt_port': '14265',
                        'zmq_socket_url': zmq_socket_url,
                        'zmq_socket_port': '5556',
                        'group': f'iota/i{(i % 2)+1}',
                        'sampling_interval': SAMPLING_INTERVAL,
                        'load_limit': LOAD_LIMIT,
                        'lb_entry_timeout': LB_ENTRY_TIMEOUT,
                        'timeout_lb_reply': TIMEOUT_LB_REPLY,
                        'timeout_gateway': TIMEOUT_GATEWAY,
                        'collect_time': COLLECT_TIME,
                        'publish_time': PUBLISH_TIME,
                        'is_balanceable': IS_BALANCEABLE,
                        'is_multi_layer': IS_MULTI_LAYER,
        }, f'188{i}')
 #       gateway.switch = f'sw-{gname}'
        gateways.append(gateway)
        gateway_virtual = exp.add_virtual_instance(f'v-{gname}')
        gateways_virtual.append(gateway_virtual)

        exp.add_docker(gateway, gateway_virtual)
        print(f'Adding gateway {gateway.ip} on {gateway_virtual.label}')

    for indice, gvirtual in enumerate(gateways_virtual):
        worker = gateways_workers[indice % len(gateways_workers)]
        worker.add(gvirtual, reachable=True)
        print(f'Adding gateway {gvirtual.label} to worker {worker.ip}')

### DEVICES CONFIGURATION
    devices = []
    current_gateway = 0
    device_count = 0
    for qtd_allowed in MAX_QTD_DEVICE_PER_GATEWAYS:
        if(qtd_allowed == 0):
            current_gateway += 0
            continue
        gateway = gateways[current_gateway]
        current_gateway += 1
        for i in range(qtd_allowed):
            print(f'Creating device:{i} at gateway {gateway.name}')
            device = createFotDevice(f'device-{device_count}', IPGen.next_ip(), {
                'broker_ip': gateway.ip,
                'port': gateway.bindings['1883'],
                'username': 'karaf',
                'password': 'karaf',
                'exp_num': EXP_NUM,
                'exp_type': EXP_TYPE,
                'exp_level': EXP_LEVEL,
                'api_url': API_URL,
                'buffer_size': BUFFER_SIZE
            })
            devices.append(device)
            device_count += 1
  
    devices_workers = []
    devices_virtual = []
    for i, worker in enumerate(MDEVICES):
        devices_workers.append(exp.add_worker(worker))
        devices_virtual.append(exp.add_virtual_instance(f'v-devices-{i}'))
    

    for i, device in enumerate(devices):
        vdevice = devices_virtual[i % len(devices_virtual)]
        exp.add_docker(device, vdevice)
        print(f'Adding device {device.name} on {vdevice.label}')

    for indice, vdevice in enumerate(devices_virtual):
        worker = devices_workers[indice % len(devices_workers)]
        worker.add(vdevice, reachable=True)
        print(f'Adding virtual instance for device {vdevice.label} to worker {worker.ip}')

### TUNNEL CONFIGURATION
    iota_workers = [iota1_worker, iota2_worker]

    for iota_worker in iota_workers:
        exp.add_tunnel(iota_worker, connector_worker)

    for iota_worker in iota_workers:
        for gateway_worker in gateways_workers:
            exp.add_tunnel(iota_worker, gateway_worker)

    for gw in gateways_workers:
        for dw in devices_workers:
            exp.add_tunnel(gw, dw)

    try:
        print("Experiment started")
        exp.start()
        print("Starting iota1")
        iota1.start_network()
        print("Starting iota2")
        iota2.start_network()
        print("Iotas started")

        start_time = datetime.now()

        input("press any key to stop experiment")
        print("Stopping the experiment...")
        exp.stop()
    except Exception as ex:
        print(ex)
    finally:
        print("Finally block...")
        exp.stop()