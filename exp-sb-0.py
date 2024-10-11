from fogledgerIota.iota.IotaBasic import (IotaBasic)
from fogledgerIota.iota.config.NodeConfig import (NodeConfig)
from fogledgerIota.iota.config.CoordConfig import (CoordConfig)
from fogledgerIota.iota.config.SpammerConfig import (SpammerConfig)
from fogledgerIota.iota.config.ApiConfig import (ApiConfig)
from fogledgerIota.iota.config.WebAppConfig import (WebAppConfig)
from typing import List
from fogbed import (
    VirtualInstance, setLogLevel, FogbedDistributedExperiment, Worker, Container, Controller
)
import signal
from datetime import datetime, timedelta
import time


setLogLevel('info')

EXP_NUM = '0'
EXP_TYPE = '0'
EXP_LEVEL = '0'
API_URL = 'https://{s}:8080/api/latency-records/records'

IS_BALANCEABLE = '0'
IS_MULTI_LAYER = '0'

COLLECT_TIME = '100'
PUBLISH_TIME = '1000'
SAMPLING_INTERVAL = '1000'
LB_ENTRY_TIMEOUT = '10'
TIMEOUT_LB_REPLY = '10'
TIMEOUT_GATEWAY = '10'
BUFFER_SIZE = '64'

DEBUG_MODE_VALUE = 'true'
INDEXES = 'LB_*'
UP_DLT_URL = ''
UP_DLT_PORT = ''
UP_ZMQ_SOCKET_URL = ''
UP_ZMQ_SOCKET_PORT = ''
DU_DLT_URL = ''
DU_DLT_PORT = ''
DU_ZMQ_SOCKET_URL = ''
DU_ZMQ_SOCKET_PORT = ''

MIOTA1 = 'larsid01'
MIOTA2 = 'larsid02'

MCONNECTOR = 'larsid03'

MGATEWAY1 = 'larsid04'
MGATEWAY2 = 'larsid05'
MGATEWAY3 = 'larsid06'
MGATEWAY4 = 'larsid07'

MGATEWAYS = [MGATEWAY1, MGATEWAY2, MGATEWAY3, MGATEWAY4]

MDEVICE1 = 'larsid08'
MDEVICE2 = 'larsid09'
MDEVICE3 = 'larsid10'
MDEVICE4 = 'larsid11'

MDEVICES = [MDEVICE1, MDEVICE2, MDEVICE3, MDEVICE4]

MEXP = 'localhost'

QTD_MAX_DEVICES = 64
QTD_DEVICES_PER_MACHINE = QTD_MAX_DEVICES // len(MGATEWAYS)
LOAD_LIMIT = '16'
MAX_QTD_DEVICE_PER_GATEWAYS = [32,32,0,0]
MAX_QTD_GATEWAYS = 4

def ip_generator():
    ip_parts = list(map(int, "10.0.0.1".split('.')))
    
    for i in range(1000):
        yield '.'.join(map(str, ip_parts))
        for j in range(3, -1, -1):
            if ip_parts[j] < 255:
                ip_parts[j] += 1
                break
            ip_parts[j] = 0

def createFotDevice(name: str, config: dict):
    return Container(
        name=name,
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
        }
    )

def createFotGatway(name: str, config: dict, mqtt_port: str = '1883'):
    return Container(
        name=name,
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
        port_bindings={'8081': '8081', '14265': '14265', '1883': mqtt_port}
    )


def create_connector():
    hornet_connector = Container(
        name='hornet_connector',
        dimage='udamasceno/hornet-connector:latest',
        environment={
            'DEBUG_MODE_VALUE': DEBUG_MODE_VALUE,
            'UP_DLT_URL': UP_DLT_URL,
            'UP_DLT_PORT': UP_DLT_PORT,
            'UP_ZMQ_SOCKET_URL': UP_ZMQ_SOCKET_URL,
            'UP_ZMQ_SOCKET_PORT': UP_ZMQ_SOCKET_PORT,
            'DU_DLT_URL': DU_DLT_URL,
            'DU_DLT_PORT': DU_DLT_PORT,
            'DU_ZMQ_SOCKET_URL': DU_ZMQ_SOCKET_URL,
            'DU_ZMQ_SOCKET_PORT': DU_ZMQ_SOCKET_PORT,
        }
    )
    return hornet_connector

def create_zmq_bridge(iota_ip: str, indexes: str, port: str = '5556'):
    return Container(
        name='zmq/'+iota_ip,
        dimage='larsid/iota-zmq-bridge:1.0.0',
        dcmd=f'/entrypoint.sh',
        port_bindings={'5556': port},
        environment={
            'MQTT_IP': iota_ip,
            'INDEXES': indexes
        }
    )

setLogLevel('info')

if (__name__ == '__main__'):

    exp = FogbedDistributedExperiment(
        controller_ip='localhost',
        controller_port=6633)

    iota1_nodes = [NodeConfig(name='node0', port_bindings={'8081': '8081', '14265': '14265', '1883': '1883'})]
    iota1 = IotaBasic(exp=exp, prefix='iota1', conf_nodes=iota1_nodes)
    iota1.name = 'i1'
    iota1.ip = MIOTA1
    UP_DLT_URL = iota1.containers['node0'].ip
    zmq1_bridge = create_zmq_bridge(UP_DLT_URL, INDEXES, UP_ZMQ_SOCKET_PORT)
    iota1_virtual = exp.add_virtual_instance('iota1')

    UP_ZMQ_SOCKET_URL = zmq1_bridge.ip
    exp.add_docker(iota1, iota1_virtual)
    exp.add_docker(zmq1_bridge, iota1_virtual)

    iota1_worker = exp.add_worker(ip=MIOTA1, controller=Controller('localhost', 6633))
    iota1_worker.add(iota1_virtual, reachable=True)

    iota2_nodes = [NodeConfig(name='node1', port_bindings={'8081': '8081', '14265': '14265', '1883': '1883'})]
    iota2 = IotaBasic(exp=exp, prefix='iota2', conf_nodes=iota2_nodes)
    iota2.name = 'i2'
    iota2.ip = MIOTA2
    DU_DLT_URL = iota2.containers['node1'].ip
    zmq2_bridge = create_zmq_bridge(DU_DLT_URL, INDEXES, DU_ZMQ_SOCKET_PORT)
    iota2_virtual = exp.add_virtual_instance('iota2')
    DU_ZMQ_SOCKET_URL = zmq2_bridge.ip

    exp.add_docker(iota2, iota2_virtual)
    exp.add_docker(zmq2_bridge, iota2_virtual)   
    iota2_worker = exp.add_worker(ip=MIOTA2, controller=Controller('localhost', 6633))
    iota2_worker.add(iota2_virtual, reachable=True)

    iota_workers = [iota1_worker, iota2_worker]

    exp.add

### Connector

    connector = create_connector()
    connector_virtual = exp.add_virtual_instance('connector')
    exp.add_docker(connector, connector_virtual)

    connector_worker = exp.add_worker(ip=MCONNECTOR, controller=Controller('localhost', 6633))

    exp.add_tunnel(iota1_worker, connector_worker)
    exp.add_tunnel(iota2_worker, connector_worker)

    UP_DLT_PORT = DU_DLT_PORT = '14265'
    UP_ZMQ_SOCKET_PORT = DU_ZMQ_SOCKET_PORT = '5556'

    gateways = []
    gateway_name = ''

    mqtt_port = '188'

    for i in range(MAX_QTD_GATEWAYS):
        dlt_url = UP_DLT_URL if i % 2 == 0 else DU_DLT_URL
        dlt_port = UP_DLT_PORT if i % 2 == 0 else DU_DLT_PORT

        zmq_socket_url = UP_ZMQ_SOCKET_URL if i % 2 == 0 else DU_ZMQ_SOCKET_URL
        zmq_socket_port = UP_ZMQ_SOCKET_PORT if i % 2 == 0 else DU_ZMQ_SOCKET_PORT
        group = ('iota/i1' if i % 2 == 0 else 'iota/i2')

        gateway = createFotGatway(f'gateway{i}', {
                        'dlt_url': dlt_url,
                        'dlt_port': dlt_port,
                        'zmq_socket_url': zmq_socket_url,
                        'zmq_socket_port': zmq_socket_port,
                        'group': group,
                        'sampling_interval': SAMPLING_INTERVAL,
                        'load_limit': LOAD_LIMIT,
                        'lb_entry_timeout': LB_ENTRY_TIMEOUT,
                        'timeout_lb_reply': TIMEOUT_LB_REPLY,
                        'timeout_gateway': TIMEOUT_GATEWAY,
                        'collect_time': COLLECT_TIME,
                        'publish_time': PUBLISH_TIME,
                        'is_balanceable': IS_BALANCEABLE,
                        'is_multi_layer': IS_MULTI_LAYER,
        }, mqtt_port+str(i))
        gateway.switch = f'gateway-{i}'
        gateways.append(gateway)



    devices = []
    for gateway, limit in zip(gateways, MAX_QTD_DEVICE_PER_GATEWAYS):
        print(f'Creating {limit} devices for gateway {gateway.ip}.')
        for i in range(limit):
            print(f'Creating device:{i}')
            device = createFotDevice(f'device-{i}', {
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

    gateways_virtual = []
    for i in range(len(MAX_QTD_DEVICE_PER_GATEWAYS)):
        gateways_virtual.append(exp.add_virtual_instance(f'gateway-{i}'))

    for gateway, virtual in zip(gateways, gateways_virtual):
        exp.add_docker(gateway, virtual)

    gateway1_worker = exp.add_worker(ip=MGATEWAY1, controller=Controller('localhost', 6633))
    gateway2_worker = exp.add_worker(ip=MGATEWAY2, controller=Controller('localhost', 6633))
    gateway3_worker = exp.add_worker(ip=MGATEWAY3, controller=Controller('localhost', 6633))
    gateway4_worker = exp.add_worker(ip=MGATEWAY4, controller=Controller('localhost', 6633))

    gateways_workers = [gateway1_worker, gateway2_worker, gateway3_worker, gateway4_worker]

    for indice, gateway in enumerate(gateways_virtual):
        worker = gateways_workers[indice % 4]
        worker.add(gateway, reachable=True)
        print(f'Adding gateway {gateway.label} to worker {worker.ip}')

    device1_worker = exp.add_worker(ip=MDEVICE1, controller=Controller('localhost', 6633))
    device2_worker = exp.add_worker(ip=MDEVICE2, controller=Controller('localhost', 6633))
    device3_worker = exp.add_worker(ip=MDEVICE3, controller=Controller('localhost', 6633))
    device4_worker = exp.add_worker(ip=MDEVICE4, controller=Controller('localhost', 6633))

    devices_workers = [device1_worker, device2_worker, device3_worker, device4_worker]
    devices_virtual = []

    for i in range(len(MDEVICES)):
        devices_virtual.append(exp.add_virtual_instance(f'devices-{i}'))

    for device, virtual in zip(devices, devices_virtual):
        exp.add_docker(device, virtual)
        print(f'Adding device {device.ip} on {virtual.label}')

    for indice, device in enumerate(devices_virtual):
        worker = devices_workers[indice % len(devices_workers)]
        worker.add(device, reachable=True)
        #print(f'Adding device {device.environment['DEVICE_ID']} to worker {worker.ip}')

    for iota_worker in iota_workers:
        for gateway_worker in gateways_workers:
            exp.add_tunnel(iota_worker, gateway_worker)

    for gw in gateways_workers:
        for dw in devices_workers:
            exp.add_tunnel(gw, dw)

    try:
        print("Experiment started")
        exp.start()
        iota1.start_network()
        iota2.start_network()

        start_time = datetime.now()

        while datetime.now() - start_time < timedelta(minutes=10):
            time_remaining = timedelta(minutes=10) - (datetime.now() - start_time)
            print(f"Time reaming: {time_remaining}")

        print("Stopping the experiment...")
        exp.stop()
    except Exception as ex:
        print(ex)
    finally:
        print("Finally block...")
        exp.stop()