import socket
import time
import sys
import server_message_pb2 as msg_pb2


class MiddlewareInterface:
    """
    Middleware interface for communicating with the server to request services.
    """
    
    def __init__(self, server_address="localhost", server_port=22000):
        """
        Initialize the middleware interface.
        
        Args:
            server_address (str): Server address (default: localhost)
            server_port (int): Server port number
        """
        self.server_address = server_address
        self.server_port = server_port
        self.bufsize = 8 * 1024
        self.message_id_counter = 1
    
    def request_service(self, service_name):
        """
        Request a service from the server.
        
        Args:
            service_name (str): Name of the service to request
            
        Returns:
            dict: Response containing status, address, port, and timestamp
            None: If the request failed
        """
        if not self.server_port:
            print("Error: Server port not specified")
            return None
            
        try:
            # Create and configure the message
            message = msg_pb2.ServerMessage()
            message.id = self.message_id_counter
            message.service = service_name
            message.timestamp = int(time.time() * 1000)  # Unix timestamp in milliseconds
            
            # Increment message ID for next request
            self.message_id_counter += 1
            
            # Serialize the message
            serialized_message = message.SerializeToString()
            
            # Connect to server and send request
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.connect((self.server_address, self.server_port))
                    print(f"Connected to server at {self.server_address}:{self.server_port}")
                    
                    # Send the request
                    sock.sendall(serialized_message)
                    print(f"Sent request for service '{service_name}' with ID {message.id}")
                    
                    # Receive the response
                    response_data = sock.recv(self.bufsize)
                    
                    if response_data:
                        # Parse the response
                        response = msg_pb2.ServerResponseMessage()
                        response.ParseFromString(response_data)
                        
                        print(f"Received response for message ID {response.id}")
                        print(f"Service status: {response.status}")
                        
                        return {
                            'id': response.id,
                            'status': response.status,
                            'address': response.address,
                            'port': response.port,
                            'timestamp': response.timestamp
                        }
                    else:
                        print("No response received from server")
                        return None
                        
                except ConnectionRefusedError:
                    print(f"Connection refused. Is the server running on {self.server_address}:{self.server_port}?")
                    return None
                except Exception as e:
                    print(f"Error during communication: {e}")
                    return None
                    
        except Exception as e:
            print(f"Error creating message: {e}")
            return None


def main():
    """
    Example usage of the middleware interface.
    """
    if len(sys.argv) < 3:
        print("Usage: python middleware_interface.py <server_port> <service_name>")
        print("Example: python middleware_interface.py 8080 service1")
        sys.exit(1)
    
    server_port = int(sys.argv[1])
    service_name = sys.argv[2]
    
    # Create middleware interface
    middleware = MiddlewareInterface(server_port=server_port)
    
    # Request the service
    print(f"Requesting service: {service_name}")
    response = middleware.request_service(service_name)
    
    if response:
        print("Request successful!")
        print(f"Response details: {response}")
    else:
        print("Request failed!")


if __name__ == "__main__":
    main()