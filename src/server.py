import socket
import sys
import server_message_pb2 as msg_pb2  # Assuming your protobuf message is defined in message.proto and compiled

ADDRESS = "localhost"
if len(sys.argv) > 1:
    PORT = int(sys.argv[1])
else:
    print("Error, specify port.")
    quit(0)

SERVER = (ADDRESS, PORT)
BUFSIZE = 8*1024

# Map service string to service class
service_map = {
    "service1": 1,
    "service2": 2,
}

val = 3
def handle_message(service: str):
    service_class = service_map.get(service)
    if service_class:
        print(f"Requested service {service}, found instance {service_class}.")
        return service_class
    else:
        print(f"Service {service} not started. Starting...")
        service_map.update(service, val)
        val += 1
        return service_map.get(service)
    
with socket.socket() as sock:
    try:
        sock.bind(SERVER)
    except:
        print(f"Failed to bind to {SERVER}")
        sys.exit(1)
        
    sock.listen()
    print(f"Server listening on {ADDRESS}:{PORT}")

    while True:
        conn, addr = sock.accept()
        with conn:
            print(f"Connected by {addr}")
            data = conn.recv(BUFSIZE)
            if data:
                msg = msg_pb2.ServerMessage()  # Replace with your actual message class
                msg.ParseFromString(data)
                print(f"[{msg.timestamp}] Received message {msg.id}:", msg.service)
                ack = handle_message(msg.service)
                response = msg_pb2.ServerResponseMessage()
                response.id = msg.id
                response.status = ack
                response.address = "NOT IMPLEMENTED"
                response.port = -1
                response.timestamp = msg.timestamp
                conn.sendall(response.SerializeToString())