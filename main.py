import main_imp
import socket
import json
import time
HOST = socket.gethostbyname(socket.gethostname())
REGISTER_PORT = 51212
ALIVE_PORT = 51213
STOCK_PORT = 51214
CONFIG_PORT = 51215
BUFFERSIZE = 2048
MAX_CLIENT = 10
DATA_PATH = "data.txt"
CONNECTION_PATH = "connection.txt"
RECONNECTION_TIMES = 3
TIMEOUT = 3
ALIVE_INTERVALL = 10
main_imp.check_connection_file(CONNECTION_PATH, HOST, REGISTER_PORT, ALIVE_PORT, STOCK_PORT, CONFIG_PORT, BUFFERSIZE,
                               MAX_CLIENT, TIMEOUT, RECONNECTION_TIMES, ALIVE_INTERVALL)
print("Connection data loaded...")
main_imp.check_data_file(DATA_PATH)
print("Data loaded...")
# Node Register receive broadcasts on port 51212
registor = main_imp.NodeRegister(CONNECTION_PATH,DATA_PATH)
# Alive Checker broadcasts on port 51213
alice = main_imp.AliveChecker(CONNECTION_PATH, DATA_PATH, ALIVE_INTERVALL)
# Command line
time.sleep(1)
while True:
    print("stock - display stock")
    print("online - display online node")
    print("power - turn a sensor on/off")
    print("mod - mod existing sensor of existing node")
    print("reboot - force specific node to reboot itself")
    #print("del - del existing node locally")
    print("close - close program")
    command = input("")
    if command == "close":
        break
    elif command == "stock":
        # stock checker broadcasts on port 51214
        main_imp.display_stock(CONNECTION_PATH, DATA_PATH, STOCK_PORT)
        # Config sender broadcasts on port 51215
    # mod existing sensor
    elif command == "mod":
        # get node
        print("Choose one of the following NODE Index :")
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input("")
        node_id = ""
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
            # get sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print("Node ID not found")
        else:
            print("Choose one of the following SENSOR Index :")
            main_imp.print_sensors_list(main_imp.find_node_by_id(node_id, DATA_PATH))
            while True:
                sensor_index = input("")
                if not main_imp.is_int(sensor_index):
                    print("Enter a valid index !")
                else:
                    # get sensor by index
                    node = main_imp.find_node_by_id(node_id, DATA_PATH)
                    sensor = main_imp.find_sensor_by_index(int(sensor_index), node)
                    if not sensor:
                        print("Sensor not found")
                    else:
                        # change setting one by one
                        for key, item in sensor.items():
                            if key in ["in", "out","status"]:
                                continue
                            new_value = input(str(key) + " : ")
                            if new_value:
                                sensor[key] = new_value
                        data = main_imp.get_obj_from_file(DATA_PATH)
                        node = main_imp.find_node_by_id(node_id,DATA_PATH)
                        main_imp.replace_sensor(int(sensor_index),sensor,node)
                        main_imp.replace_node(node_id, node, data)
                        main_imp.set_obj_in_file(data, DATA_PATH)
                        # push update
                        update = [node_id, node["sensors"]]
                        main_imp.broadcast_message(CONFIG_PORT,json.dumps(update))
                    break

    # turning existing sensor on / off
    elif command == "power":
        # get node
        print("Choose one of the following NODE Index :")
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input("")
        node_id = ""
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
        # show sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print("Node ID not found")
        else:
            while True:
                print("Choose one of the following SENSOR Index :")
                main_imp.print_sensors_list(main_imp.find_node_by_id(node_id, DATA_PATH))
                sensor_index = input("")
                if not main_imp.is_int(sensor_index):
                    print("Enter a valid index !")
                    continue
                node = main_imp.find_node_by_id(node_id, DATA_PATH)
                sensor = main_imp.find_sensor_by_index(int(sensor_index), node)
                if not sensor:
                    print("This sensor not found")
                    continue
                if sensor["status"] == "online":
                    sensor["status"] = "offline"
                else:
                    sensor["status"] = "online"

                data = main_imp.get_obj_from_file(DATA_PATH)
                node = main_imp.find_node_by_id(node_id, DATA_PATH)
                main_imp.replace_sensor(int(sensor_index),sensor,node)
                main_imp.replace_node(node_id, node, data)
                main_imp.set_obj_in_file(data, DATA_PATH)
                print("Sensor Status changed to",sensor["status"])
                # push update
                update = [node_id, node["sensors"]]
                main_imp.broadcast_message(CONFIG_PORT, json.dumps(update))
                break
    elif command == "del":
        # get node
        print("Choose one of the following NODE Index :")
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input("")
        node_id = ""
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
        # show sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print("Node ID not found")
        else:
            data = main_imp.get_obj_from_file(DATA_PATH)
            for i in range(len(data)):
                node = data[i]
                if node["id"] == node_id:
                    del data[i]
                    break
            main_imp.set_obj_in_file(data,DATA_PATH)
            print("Node",node_id,"deleted")

    elif command == "online":
        data = main_imp.get_obj_from_file(DATA_PATH)
        for node in data:
            print(str(node["id"])," : ",node["status"])
        print()

    elif command == "reboot":
        print("Choose one of the following NODE Index :")
        main_imp.print_nodes_list(DATA_PATH)
        node_input = input("")
        node_id = ""
        if main_imp.is_int(node_input):
            node_id = main_imp.find_node_id_by_index(int(node_input), DATA_PATH)
        else:
            node_id = node_input
        # show sensor
        if not main_imp.is_node_in_list(node_id, DATA_PATH):
            print("Node ID not found")
        else:
            main_imp.broadcast_message(CONFIG_PORT, node_id)