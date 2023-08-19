import os
import shutil
import socket
import yaml


def read_lab_config(lab_id):
    """
    Read the YAML configuration file for the specified lab.

    :param lab_id: The ID of the lab (e.g., "lab1")
    :return: A dictionary containing the lab configuration
    """
    config_dir = os.path.join(os.path.dirname(__file__), '../lab_configs')
    config_file = os.path.join(config_dir, f"{lab_id}.yaml")

    with open(config_file, 'r') as f:
        lab_config = yaml.safe_load(f)

    return lab_config


def create_directory(path):
    """
    Create a directory if it does not already exist.

    :param path: The path to the directory
    """
    if not os.path.exists(path):
        os.makedirs(path)


def delete_directory(path):
    """
    Delete a directory if it exists.

    :param path: The path to the directory
    """
    if os.path.exists(path):
        shutil.rmtree(path)


def read_file(file_path):
    """
    Read the contents of a file.

    :param file_path: The path to the file
    :return: A string containing the contents of the file
    """
    with open(file_path, 'r') as f:
        return f.read()


def write_file(file_path, content):
    """
    Write the contents to a file.

    :param file_path: The path to the file
    :param content: The content to be written
    """
    with open(file_path, 'w') as f:
        f.write(content)


def append_to_file(file_path, content):
    """
    Append the contents to a file.

    :param file_path: The path to the file
    :param content: The content to be appended
    """
    with open(file_path, 'a') as f:
        f.write(content)


# function to find available ports that are not in use on the system and is in the specified range.

def get_available_ports(start=8000, end=9000, count=1, exclude=[]):
    """
    Find available ports that are not in use on the system and is in the specified range.

    :param start: The start of the port range
    :param end: The end of the port range
    :param count: The number of ports to find
    :return: A list of available ports
    """
    ports = []
    for port in range(start, end):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        if result != 0 and port not in exclude:
            ports.append(port)
        sock.close()
        if len(ports) == count:
            break
    if len(ports) < count:
        raise Exception(f"Could not find {count} available ports in the range {start}-{end}")
    return ports

