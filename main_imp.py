import socket
import json
import os.path
import os
import threading
import time
import select
import zipfile
import platform


# -----------------------------------------------FILE--------------------------------------------------------------------

# this function return an object from file
def get_obj_from_file(file_path: str):
    file = None
    if os.path.isfile(file_path):
        with open(file_path, 'r') as file:
            file = json.loads(file.read())
    return file


# this function overwrite a file with a new object
def set_obj_in_file(obj, file_path: str):
    with open(file_path, 'w') as file:
        file.write(json.dumps(obj, indent=1))


# this function creates connection file for center app
# only when no file is found
def check_connection_file(connect_file: str, host, port, a_port, buffer: int,
                          max_client: int, timeout, reconnect,
                          alive_interval):
    data = {'host': host, 'port': port, 'a_port': a_port,
            'buffersize': buffer, 'max_client': max_client, 'timeout': timeout, 'reconnect': reconnect,
            'alive_interval': alive_interval}
    set_obj_in_file(data, connect_file)


# this function create a empty data file
# only when no file is found
def check_data_file(data_file: str):
    if not os.path.isfile(data_file):
        data = []
        set_obj_in_file(data, data_file)


def check_update_setting_file(update_setting_file: str, update_directory: str, update_filename: str,
                              node_directory: str, node_file_list: list):
    if not os.path.isfile(update_setting_file):
        data = {'update_dir': update_directory, 'update_filename': update_filename,
                'node_dir': node_directory, 'node_file_list': node_file_list}
        set_obj_in_file(data, update_setting_file)


def run_sh_script(script_name):
    os.system(script_name)


def zip_files(file_path: str, zip_name: str) -> bool:
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as target_zip:
        for root, dirs, files in os.walk('.\\' + file_path):
            for file in files:
                target_zip.write(os.path.join(root, file))
    return True


# this func copies the updates in a specific directory
def center_local_updates(node_dir: str, file_list: list):
    for filename in file_list:
        if platform.system() == 'Windows':
            os.system('copy ..\\' + node_dir + '\\' + filename + ' .\\updates\\')
        elif platform.system() == 'Linux':
            os.system('copy ..\\' + node_dir + '\\' + filename + ' .\\updates\\')
        else:
            print('cant not determine which operation system')
            break


# -----------------------------------------------VALUE CHECK------------------------------------------------------------


def is_int(text: str):
    try:
        int(text)
        return True
    except ValueError:
        return False


def is_gpio_port(str_value):
    value = int(str_value)
    return 0 < value <= 60


def is_json(json_string: str) -> bool:
    try:
        json.loads(json_string)
        return True
    except ValueError:
        return False


def is_new_version(current_version: str, target_version: str)->bool:
    new_version = True
    if target_version[0] != 'v':
        return False
    if current_version != target_version:
        for i in range(1, len(current_version)):
            if current_version[i] != target_version[i]:
                try:
                    if int(current_version[i]) > int(target_version[i]):
                        new_version = False
                except ValueError:
                    return False
    return new_version
# -----------------------------------------------TCP---------------------------------------------------------------------


def get_host_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    host = s.getsockname()[0]
    s.close()
    return host


# tcp single packet receive

# tcp multiple receive using select
def tcp_select_receive(host, port, buffersize, timeout, max_client):
    results = []
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(max_client)
    server.setblocking(0)
    server_input = [server]
    running = 1

    while running:
        input_ready, output_ready, except_ready = select.select(server_input, [], [], timeout)
        if not (input_ready or output_ready or except_ready):
            server.close()
            break
        for s in input_ready:
            if s == server:
                # handle the server socket
                client, address = server.accept()
                server_input.append(client)
            else:
                # handle all other sockets
                data = s.recv(buffersize)
                if data:
                    message = data.decode()
                    results.append(message)
                else:
                    s.close()
                    server_input.remove(s)
    return results


# this func sends a message over TCP
def tcp_send(host, port, message: str, timeout, reconnect) -> bool:
    for i in range(reconnect):
        sock = socket.socket()
        try:

            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(message.encode())
            sock.close()
            return True
        except socket.timeout:
            sock.close()
        except socket.error:
            sock.close()
    return False


# this func sends a file over TCP
def tcp_send_file(host, port, file_path: str, buffersize: int, timeout, reconnect) -> bool:
    for i in range(reconnect):
        sock = socket.socket()
        try:
            sock.settimeout(timeout)
            sock.connect((host, port))
            file = open(file_path, 'rb')
            while True:
                file_part = file.read(buffersize)
                if not file_part:
                    break
                sock.send(file_part)
            file.close()
            sock.close()
            return True
        except socket.timeout:
            sock.close()
        except socket.error:
            sock.close()
    return False


# -----------------------------------------------UDP---------------------------------------------------------------------


# this func broadcast a message over udp
def broadcast_message(port, message: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    # sock.bind((host, port))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # broad cast a message over the network
    # checking if any node is alive
    try:
        sock.sendto(message.encode(), ('<broadcast>', port))
        sock.close()
    except socket.error:
        sock.close()

# -----------------------------------------------NODE--------------------------------------------------------------------


# this func print a node list
def print_nodes_list(data_path: str):
    data = get_obj_from_file(data_path)
    assert isinstance(data, list)
    print('INDEX        NODE        STATUS')
    for i in range(len(data)):
        node = data[i]
        print(str(i), '\t', str(node[0]), '\t', str(node[1]))


# this func marks a node with a given status
def mark_node(node_id: str, data_file: str, status: str):
    data = get_obj_from_file(data_file)
    for i in range(len(data)):
        node = data[i]
        if node[0] == node_id:
            node[1] = status
    set_obj_in_file(data, data_file)


# this func replace a node in database
def replace_node(node_id: str, new_node: dict, data: list) -> bool:
    for i in range(len(data)):
        old_node = data[i]
        if old_node['id'] == node_id:
            data[i] = new_node
            return True


# thi func determines if a node exist in data or not
def is_node_in_list(node_id: str, data_file: str):
    data = get_obj_from_file(data_file)
    for node in data:
        if node[0] == node_id:
            return True
    return False


# this function find object with the given ID
# return null when the expected object is not found
def find_node_by_id(node_id: str, data_file: str):
    data = get_obj_from_file(data_file)
    for i in range(len(data)):
        node = data[i]
        if node['id'] == node_id:
            return node
    return None


def find_node_id_by_index(index: int, data_file: str):
    data = get_obj_from_file(data_file)
    try:
        node = data[index]
        return node[0]
    except IndexError:
        return None


# -----------------------------------------------SENSOR-----------------------------------------------------------------

def find_sensor_by_index(sensor_index: int, node: dict):
    sensor_list = node['sensors']
    for i in range(len(sensor_list)):
        if i == sensor_index:
            return sensor_list[i]
    return None


def remove_sensor_by_index(sensor_index: int, node: dict) -> bool:
    sensor_list = node['sensors']
    for i in range(len(sensor_list)):
        if i == sensor_index:
            del sensor_list[i]
            return True
    return False


# this func replace a sensor in a node
def replace_sensor(sensor_index: int, new_sensor: dict, node: dict):
    sensor_list = node['sensors']
    try:
        sensor_list[sensor_index] = new_sensor
    except IndexError:
        sensor_list.append(new_sensor)


# -----------------------------------------------CENTER------------------------------------------------------------------

def refresh_database(connection_file: str, data_file: str):
    connection_data = get_obj_from_file(connection_file)
    host = connection_data['host']
    port = connection_data['port']
    max_client = connection_data['max_client']
    buffersize = connection_data['buffersize']
    timeout = connection_data['timeout']
    broadcast_message(port, 'DATAS?' + host)
    results = tcp_select_receive(host, port, buffersize, timeout, max_client)
    data = get_obj_from_file(data_file)
    # for node in data:
    #    node[1] = 'offline'
    for result in results:
        if result[:5] != 'DATASY':
            continue
        node_id = result[5:]
        if is_node_in_list(node_id, data_file):
            for node in data:
                if node[0] == node_id:
                    node[1] = 'online'
                    break
        else:
            new_node = [node_id, 'online']
            data.append(new_node)
    set_obj_in_file(data, data_file)


def get_sensors_of_node(node_id: str, connection_file: str) -> list:
    connection_data = get_obj_from_file(connection_file)
    host = connection_data['host']
    port = connection_data['port']
    max_client = connection_data['max_client']
    buffersize = connection_data['buffersize']
    timeout = connection_data['timeout']
    package = ['SENSOR', node_id, host]
    broadcast_message(port, json.dumps(package))
    results = tcp_select_receive(host, port, buffersize, timeout, max_client)
    if results:
        return json.loads(results[0])
    return None


# this thread broadcasts a signal to all available nodes
# to determine the online status of all nodes in the network
# the broadcasting stop when time passed
# this thread then waits for answer from nodes via TCP
# waiting time is double of time out duration
class AliveChecker(threading.Thread):
    def __init__(self, connection_file, data_file, update_setting_file, alive_interval, version):
        threading.Thread.__init__(self)
        self.connection_file = connection_file
        self.data_file = data_file
        self.update_setting_file = update_setting_file
        self.alive_interval = alive_interval
        connect_data = get_obj_from_file(connection_file)
        self.host = connect_data['host']
        self.a_port = connect_data['a_port']
        self.buffersize = connect_data['buffersize']
        self.max_client = connect_data['max_client']
        self.timeout = connect_data['timeout']
        self.reconnect = connect_data['reconnect']
        self.version = version
        self.daemon = 1
        self.start()

    def run(self):
        message = 'ALIVE?' + self.host
        while True:
            broadcast_message(self.a_port, message)

            # waiting for replies from node in network
            # from the received id, mark nodes as online or offline
            # print('Start listening to survivors')
            survivors_list_raw = tcp_select_receive(self.host, self.a_port, self.buffersize, self.timeout,
                                                    self.max_client)
            survivors_list = []
            version_list = []
            for survivor in survivors_list_raw:
                survivors_list.append(survivor[4:])
                version_list.append(survivor[:4])
            # print('Survivor : ', str(survivors_list))
            # recruit new survivors
            data = get_obj_from_file(self.data_file)
            for survivor in survivors_list:
                if not is_node_in_list(survivor, self.data_file):
                    data.append([survivor, 'online'])
            set_obj_in_file(data, self.data_file)
            # marking node as online or offline
            for node in data:
                node_id = node[0]
                if node_id in survivors_list:
                    mark_node(node_id, self.data_file, 'online')
                else:
                    if is_node_in_list(node_id, self.data_file):
                        mark_node(node_id, self.data_file, 'offline')

            # issues updates
            to_be_updated_nodes = []
            for i in range(len(version_list)):
                version = version_list[i]
                if not is_new_version(self.version, version):
                    to_be_updated_nodes.append(survivors_list[i])
            if to_be_updated_nodes:
                update_settings = get_obj_from_file(self.update_setting_file)

                update_nodes(to_be_updated_nodes, self.connection_file,
                             update_settings['node_dir'], update_settings['node_file_list'],
                             update_settings['update_dir'], update_settings['update_filename'])
            time.sleep(self.alive_interval)


# this func display the current stock
def display_stock(connection_file, data_file, port):
    connection_data = get_obj_from_file(connection_file)
    host = connection_data['host']
    buffersize = connection_data['buffersize']
    timeout = connection_data['timeout']
    max_client = connection_data['max_client']
    message = 'STOCK?' + host
    # asks all nodes for stocks
    broadcast_message(port, message)
    print('Loading Stock...')
    stock_list = tcp_select_receive(host, port, buffersize, timeout, max_client)
    print('Stock List')
    data = get_obj_from_file(data_file)
    for node in data:
        node_id = node[0]
        print('NODE ', node_id, ':')
        for answer in stock_list:
            content = json.loads(answer)
            if node_id == content[0]:
                stocks = content[1]
                for i in range(len(stocks)):
                    if isinstance(stocks[i], str):
                        print('\t', str(i), 'has', stocks[i])
                    elif stocks[i] == -1:
                        print('\t', str(i), 'has GPIO Error')
                    elif stocks[i] == -2:
                        print('\t', str(i), 'is timed out')
                    elif stocks[i] == -3:
                        print('\t', str(i), 'incorrect configuration (value below zero)')
                    elif stocks[i] == -4:
                        print('\t', str(i), 'incorrect configuration (item is larger then its container)')
                    elif stocks[i] == -5:
                        print('\t', str(i), 'Arithmetic Error')
                    elif stocks[i] <= 1:
                        print('\t', str(i), 'has', str(stocks[i]), 'item')
                    elif stocks[i] > 1:
                        print('\t', str(i), 'has', str(stocks[i]), 'items')


# update a specific list of nodes
def update_nodes(nodes_list: list, connection_file: str,
                 node_directory: str, node_file_list: list, updates_directory: str, updates_filename: str):
    connection_data = get_obj_from_file(connection_file)
    host = connection_data['host']
    port = connection_data['port']
    buffersize = connection_data['buffersize']
    timeout = connection_data['timeout']
    max_client = connection_data['max_client']
    reconnect = connection_data['reconnect']
    # copy updates to center directory
    center_local_updates(node_directory, node_file_list)
    # notifies nodes
    package = ['UPDATE', nodes_list, host]
    broadcast_message(port, json.dumps(package))
    # receives confirmation
    results = tcp_select_receive(host, port, buffersize, timeout, max_client)
    for result in results:
        print(str(result), 'received the update...')
    # zips updates
    zip_files(updates_directory, updates_filename)
    # sends updates
    for result in results:
        tcp_send_file(result, port, updates_filename, buffersize, timeout, reconnect)
