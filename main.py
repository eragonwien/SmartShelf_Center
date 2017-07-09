import main_imp
import socket
import json
import time
#####
HOST = socket.gethostbyname(socket.gethostname())
print(HOST)
VERSION = 'v1.6'
PORT = 51212
A_PORT = 51213
BUFFERSIZE = 2048
MAX_CLIENT = 10
DATA_PATH = 'data.txt'
CONNECTION_PATH = 'connection.txt'
RECONNECTION_TIMES = 3
TIMEOUT = 3
ALIVE_INTERVAL = 10
#####
UPDATE_SETTING_FILE = 'update_setting.txt'
UPDATES_DIR = 'updates'
UPDATES_FILENAME = 'updates.zip'
NODE_DIR = 'SmartShelf_Node'
NODE_FILE_LIST = ['node.py', 'node_imp.py', 'sonic_measure.py']
#####
main_imp.check_connection_file(CONNECTION_PATH, HOST, PORT, A_PORT, BUFFERSIZE, MAX_CLIENT, TIMEOUT, RECONNECTION_TIMES,
                               ALIVE_INTERVAL)
print('Connection data loaded...')
main_imp.check_data_file(DATA_PATH)
print('Data loaded...')
main_imp.check_update_setting_file(UPDATE_SETTING_FILE, UPDATES_DIR, UPDATES_FILENAME, NODE_DIR, NODE_FILE_LIST)
# Alive Checker broadcasts on port 51213
alice = main_imp.AliveChecker(CONNECTION_PATH, DATA_PATH, UPDATE_SETTING_FILE, ALIVE_INTERVAL, VERSION)
# Command line
time.sleep(1)
while True:
    print('stock - display stock')
    print('online - display online node')
    print('mod - mod existing sensor of existing node')
    print('update - force specific node to update and reboot itself')
    print('test - test node')
    print('close - close program')
    command = input('')
    if command == 'check':
        print(main_imp.get_obj_from_file(DATA_PATH))
    if command == 'close':
        break
    elif command == 'online':
        data = main_imp.get_obj_from_file(DATA_PATH)
        for node in data:
            print(node[0], 'is', node[1])
        print()
    elif command == 'stock':
        main_imp.display_stock(CONNECTION_PATH, DATA_PATH, PORT)
    # mod existing sensor
    elif command == 'mod':
        # get node
        print('Loading data ...')
        main_imp.refresh_database(CONNECTION_PATH, DATA_PATH)
        print('Choose one of the following NODE Index :')
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input('')
        node_id = ''
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
            # get sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print('Node ID not found')
        else:
            print('Loading Sensors ...')
            sensor_list = main_imp.get_sensors_of_node(node_id, CONNECTION_PATH)
            if not sensor_list:
                print('Node', str(node_id), 'did not respond')
                continue
            print('Choose one of the following SENSOR Index :')
            for i in range(len(sensor_list)):
                sensor = sensor_list[i]
                print(str(i), 'item_width :', sensor['item_width'], 'shelf width :', sensor['shelf_width'])
            while True:
                sensor_index = input('')
                if not main_imp.is_int(sensor_index) or not (int(sensor_index) in range(len(sensor_list))):
                    print('Enter a valid index !')
                else:
                    # get sensor by index
                    sensor = sensor_list[int(sensor_index)]
                    # change setting one by one
                    for key, item in sensor.items():
                        if key in ['in', 'out', 'status']:
                            continue
                        new_value = input(str(key) + ' : ')
                        if new_value:
                            sensor[key] = new_value
                    package = ['CHANGE' + HOST, (node_id, sensor_index), sensor]
                    main_imp.broadcast_message(PORT, json.dumps(package))
                    answers = main_imp.tcp_select_receive(HOST, PORT, BUFFERSIZE, TIMEOUT, MAX_CLIENT)
                    if answers:
                        answer = answers[0]
                        if answer[:2] == 'OK' and answer[2:] == node_id:
                            print('Changes of', node_id, ' was pushed successfully')
                        else:
                            print('Changes of', node_id, 'was not pushed')
                    else:
                        print('Changes of', node_id, 'was not received')
                    break

    elif command == 'del':

        print('Loading data ...')
        main_imp.refresh_database(CONNECTION_PATH, DATA_PATH)
        # get node
        print('Choose one of the following NODE Index :')
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input('')
        node_id = ''
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
        # show sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print('Node ID not found')
        else:
            data = main_imp.get_obj_from_file(DATA_PATH)
            for i in range(len(data)):
                node = data[i]
                if node['id'] == node_id:
                    del data[i]
                    break
            main_imp.set_obj_in_file(data, DATA_PATH)
            print('Node', node_id, 'deleted')

    elif command == 'shutdown':
        # get node
        print('Choose one of the following NODE Index :')
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input('')
        node_id = ''
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
        # show sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print('Node ID not found')
        else:
            main_imp.broadcast_message(PORT, 'SHUTD?' + node_id)
            answers = main_imp.tcp_select_receive(HOST, PORT, BUFFERSIZE, TIMEOUT, MAX_CLIENT)
            if answers:
                answer = answers[0]
                if answer[:6] == 'SHUTDY' and answer[6:] == node_id:
                    print(node_id, 'is going to be shutdown !')
                else:
                    print(node_id, 'failed to be shutdown')
            else:
                print(node_id, 'did not respond to shutdown command')
    elif command == 'update':
        node_list = []
        for node in main_imp.get_obj_from_file(DATA_PATH):
            node_list.append(node[0])
        main_imp.update_nodes(node_list, CONNECTION_PATH,
                              NODE_DIR, NODE_FILE_LIST, UPDATES_DIR, UPDATES_FILENAME)
    elif command == 'test':
        main_imp.broadcast_message(PORT, 'TESTST' + HOST)
        results = main_imp.tcp_select_receive(HOST, PORT, BUFFERSIZE, TIMEOUT, MAX_CLIENT)
        for result in results:
            if not main_imp.is_json(result):
                print('ERROR')
                continue
            result_content = json.loads(result)
            (node_id, node_version) = result_content
            print(node_id, 'has version', node_version)
