import socket
import json
import os.path
import threading
import time
import select


# -----------------------------------------------FILE--------------------------------------------------------------------

# this function return an object from file
def get_obj_from_file(filepath: str):
    file = None
    if os.path.isfile(filepath):
        with open(filepath, "r") as file:
            file = json.loads(file.read())
    return file


# this function overwrite a file with a new object
def set_obj_in_file(obj, filepath: str):
    with open(filepath, "w") as file:
        file.write(json.dumps(obj, indent=1))


# this function creates connection file for center app
# only when no file is found
def check_connection_file(connect_file: str, host, port, alive_port, stock_port, config_port, buffer: int,
                          max_client: int, timeout, reconnect,
                          alive_intervall):
    data = {"host": host, "port": port, "alive_port": alive_port, "stock_port": stock_port,
            "config_port": config_port,
            "buffersize": buffer, "max_client": max_client, "timeout": timeout, "reconnect": reconnect,
            "alive_intervall": alive_intervall}
    set_obj_in_file(data, connect_file)


# this function create a basic setting file
# when no setting file is found
def check_setting_file(settingpath: str, alive_intervall):
    setting = get_obj_from_file(settingpath)
    if not setting:
        setting = {"alive_intervall": alive_intervall}
        set_obj_in_file(setting, settingpath)


# this function create a empty data file
# only when no file is found
def check_data_file(datapath: str):
    if not os.path.isfile(datapath):
        data = []
        set_obj_in_file(data, datapath)

def run_sh_script(script_name):
    os.system(script_name)
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


# -----------------------------------------------TCP---------------------------------------------------------------------


# tcp receive using select
def tcp_select_receive(host, port, buffersize, timeout, max_client):
    results = []
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(max_client)
    input = [server]
    running = 1
    while running:
        inputready, outputready, exceptready = select.select(input, [], [], timeout)
        if not (inputready or outputready or exceptready):
            server.close()
            break
        for s in inputready:
            if s == server:
                # handle the server socket
                client, address = server.accept()
                input.append(client)
            else:
                # handle all other sockets
                data = s.recv(buffersize)
                if data:
                    message = data.decode()
                    results.append(message)
                else:
                    s.close()
                    input.remove(s)
    return results


# this func receive multiple TCP message
def tcp_multi_receive(host, port, buffersize, timeout, max_client):
    content = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout != 0:
        sock.settimeout(timeout)
    sock.bind((host, port))
    sock.listen(max_client)
    try:
        while 1:
            conn, addr = sock.accept()
            TCPReceiveThread(conn, buffersize, content)
    except socket.timeout:
        sock.close()
    return content


class TCPReceiveThread(threading.Thread):
    def __init__(self, conn, buffersize, content):
        threading.Thread.__init__(self)
        self.conn = conn
        self.buffersize = buffersize
        self.content = content
        self.terminate = False
        self.daemon = True
        self.start()

    def run(self):
        while not self.terminate:
            message = self.conn.recv(self.buffersize)
            if not message:
                break
            self.add_value_to_content(message.decode())

    def terminate(self):
        self.terminate = True

    def add_value_to_content(self, value):
        self.content.append(value)


# this func send a message over TCP
def tcp_send(host, port, message: str, timeout, reconnect) -> bool:
    for i in range(reconnect):
        sock = socket.socket()
        try:

            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(message.encode())
            sock.close()
            return True
        except:
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
        sock.sendto(message.encode(), ("<broadcast>", port))
        sock.close()
    except socket.error:
        sock.close()


# -----------------------------------------------NODE--------------------------------------------------------------------


# this func print a node list
def print_nodes_list(datapath: str):
    data = get_obj_from_file(datapath)
    assert isinstance(data, list)
    print("INDEX        NODE")
    for i in range(len(data)):
        node = data[i]
        node_id = node["id"]
        print(str(i), "      ", str(node_id))


# this func create new node with default infomation
def create_new_default_node(id: str, pin_list: list, datapath: str) -> dict:
    sensor_list = []
    for pin_dual in pin_list:
        sensor = {"in": pin_dual[0], "out": pin_dual[1], "status": "offline", "item_width": 0, "shelf_width": 0}
        sensor_list.append(sensor)
    node = {"id": id, "sensors": sensor_list, "status": "online"}
    return node


# this func register new node in datapath with default infomation
def register_new_node(node: dict, datapath: str):
    data = get_obj_from_file(datapath)
    data.append(node)
    set_obj_in_file(data, datapath)
    return True


# this func marks a node with a given status
def mark_node(node_id: str, datapath: str, status: str):
    data = get_obj_from_file(datapath)
    for i in range(len(data)):
        node = data[i]
        if node["id"] == node_id:
            node["status"] = status
    set_obj_in_file(data, datapath)


# this func replace a node in database
def replace_node(node_id: str, new_node: dict, data: list) -> bool:
    for i in range(len(data)):
        old_node = data[i]
        if old_node["id"] == node_id:
            data[i] = new_node
            return True


# thi func determines if a node exist in0 a list or not
def is_node_in_list(node_id: str, datapath: str):
    data = get_obj_from_file(datapath)
    for node in data:
        if node["id"] == node_id:
            return True
    return False


# this function find object with the given ID
# return null when the expected object is not found
def find_node_by_id(node_id: str, datapath: str):
    data = get_obj_from_file(datapath)
    for i in range(len(data)):
        node = data[i]
        if node["id"] == node_id:
            return node
    return None


def find_node_id_by_index(index: str, datapath: str):
    data = get_obj_from_file(datapath)
    assert is_int(index)
    try:
        node = data[int(index)]
        return node["id"]
    except IndexError:
        return None


# -----------------------------------------------SENSOR------------------------------------------------------------------


# this func print a sensor list
def print_sensors_list(node: dict):
    sensor_list = node["sensors"]
    assert isinstance(sensor_list, list)
    print("INDEX        SENSOR")
    for i in range(len(sensor_list)):
        print(str(i), "      ", str((sensor_list[i])["status"]))


def find_sensor_by_index(sensor_index: int, node: dict):
    sensor_list = node["sensors"]
    for i in range(len(sensor_list)):
        if i == sensor_index:
            return sensor_list[i]
    return None


def remove_sensor_by_index(sensor_index: int, node: dict) -> bool:
    sensor_list = node["sensors"]
    for i in range(len(sensor_list)):
        if i == sensor_index:
            del sensor_list[i]
            return True
    return False


# this func replace a sensor in a node
def replace_sensor(sensor_index: int, new_sensor: dict, node: dict):
    sensor_list = node["sensors"]
    try:
        sensor_list[sensor_index] = new_sensor
    except IndexError:
        sensor_list.append(new_sensor)


# this func add new sensor to node
def add_new_sensor(node_id: str, sensor: dict, connectionpath: str, datapath: str) -> bool:
    # get node
    node = find_node_by_id(node_id, datapath)
    if not node:
        return False
    # ID
    # add new config to sensor
    node["sensors"].append(sensor)
    # add node to data
    data = get_obj_from_file(datapath)
    replace_node(node_id, node, data)
    set_obj_in_file(data, datapath)
    # push node
    sensor_list = node["sensors"]
    message = json.dumps(sensor_list, indent=1)
    try:
        connection_data = get_obj_from_file(connectionpath)
        broadcast_message(connection_data["port"], message)
    except:
        return False
    return True


# -----------------------------------------------CENTER------------------------------------------------------------------

# this thread listens to node broadcasting infomation
# on receiving nodes information, this thread sends a pakage back
# the package contains settings and configuration for the node
class NodeRegister(threading.Thread):
    def __init__(self, connectpath, datapath):
        threading.Thread.__init__(self)
        self.connectpath = connectpath
        self.datapath = datapath
        connect_data = get_obj_from_file(connectpath)
        self.host = connect_data["host"]
        self.port = connect_data["port"]
        self.buffersize = connect_data["buffersize"]
        self.max_client = connect_data["max_client"]
        self.timeout = connect_data["timeout"]
        self.reconnect = connect_data["reconnect"]
        self.daemon = 1
        self.start()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', self.port))
        while 1:
            try:
                # receive any broadcast call
                message = sock.recvfrom(self.buffersize)
                message_content = message[0].decode()
                # print("Received Register: ", message_content)
                if not is_json(message_content):
                    continue
                received_package = json.loads(message_content)
                node_id = received_package[0]
                pin_list = received_package[1]
                # check id
                is_new_node = False
                node = find_node_by_id(node_id, self.datapath)
                # if no create basic node
                if not node:
                    node = create_new_default_node(node_id, pin_list, self.datapath)
                    is_new_node = True
                package = [node]
                print("Sending...")
                if tcp_send(node_id, self.port, json.dumps(package, indent=1), self.timeout, self.reconnect):
                    if is_new_node:
                        print(node_id, "registered...")
                    else:
                        print(node_id, "updated...")
                    if is_new_node:
                        register_new_node(node, self.datapath)
                    mark_node(node_id, self.datapath, "online")
                else:
                    if is_new_node:
                        print("not registed")
                    else:
                        print("not updated")
            except socket.error:
                sock.close()


# this thread broadcasts a signal to all available nodes
# to determine the online status of all nodes in the network
# the broadcasting stop when time passed
# this thread then waits for answer from nodes via TCP
# waiting time is double of time out duration
class AliveChecker(threading.Thread):
    def __init__(self, connectpath, datapath, alive_intervall):
        threading.Thread.__init__(self)
        self.connectpath = connectpath
        self.datapath = datapath
        self.alive_intervall = alive_intervall
        connect_data = get_obj_from_file(connectpath)
        self.host = connect_data["host"]
        self.port = connect_data["alive_port"]
        self.buffersize = connect_data["buffersize"]
        self.max_client = connect_data["max_client"]
        self.timeout = connect_data["timeout"]
        self.reconnect = connect_data["reconnect"]
        self.daemon = 1
        self.start()

    def run(self):
        message = "ALIVE" + self.host
        while True:
            broadcast_message(self.port, message)

            # waiting for replies from node in network
            # from the received id, mark nodes as online or offline
            # print("Start listening to survivors")
            survivors_list = tcp_select_receive(self.host, self.port, self.buffersize, self.timeout, self.max_client)
            # print("Survivor : ", str(survivors_list))
            # mark survivors as online in database
            data = get_obj_from_file(self.datapath)
            for node in data:
                node_id = node["id"]
                if node_id in survivors_list:
                    mark_node(node_id, self.datapath, "online")
                else:
                    if is_node_in_list(node_id, self.datapath):
                        mark_node(node_id, self.datapath, "offline")
            time.sleep(self.alive_intervall)


# this func display the current stock
def display_stock(connectionpath, datapath, port):
    connection_data = get_obj_from_file(connectionpath)
    host = connection_data["host"]
    buffersize = connection_data["buffersize"]
    timeout = connection_data["timeout"]
    max_client = connection_data["max_client"]
    message = "STOCK" + connection_data["host"]
    broadcast_message(port, message)
    print("Loading Stock...")
    stock_list = tcp_select_receive(host, port, buffersize, timeout, max_client)
    print("Stock List")
    data = get_obj_from_file(datapath)
    for node in data:
        if node["status"] == "offline":
            print("NODE Nr.",str(node["id"]),"is offline")
        else :
            print("NODE Nr.",str(node["id"]))
            sensor_list = node["sensors"]
            for json_result in stock_list:
                result = json.loads(json_result)
                if result[0] == node["id"]:
                    for i in range(1,len(result)):
                        sensor = sensor_list[i - 1]
                        if sensor["status"] == "offline":
                            print(str(i-1),"is offline")
                            continue
                        item_stock = int(result[i])
                        if item_stock <= 1 :
                            print(str(i-1),"has",str(item_stock),"item")
                        else:
                            print(str(i-1),"has",str(item_stock),"items")