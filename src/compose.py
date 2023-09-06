import os
import subprocess
import yaml
from nginx import NginxConfig
from utils import get_available_ports
from lab_config import config
from fnmatch import fnmatch
import docker
from jinja2 import Template

client = docker.from_env()
os.makedirs('tmp', exist_ok=True)
nginx = NginxConfig()  # create nginx config object to manage lab server blocks


def create_student_container(student_id, lab_id, norestart=False, save=True, template=None):
    # get the domain from the config file
    domain = config.get('domain', 'example.com')

    lab_config = find_lab_config(lab_id)

    if template is None:
        docker_compose_template_path = os.path.join('lab_configs', lab_config['docker_compose'])
        # If the template file doesn't exist, raise an error
        if not os.path.exists(docker_compose_template_path):
            raise ValueError(f"Could not find docker compose template at {docker_compose_template_path}")

        template = Template(open(docker_compose_template_path).read())

    existing_containers = {c.name for c in client.containers.list(all=True)}

    container_name = f"{student_id}-{lab_id}"

    if container_name in existing_containers:
        print(f"Skipping existing container for student {student_id} and lab {lab_id}.")
        # TODO: add else block

    # Get the directory where compose.py is located
    compose_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory of the compose directory
    parent_dir = os.path.dirname(compose_dir)

    # Create the tmp directory inside the parent directory if it doesn't exist
    tmp_dir = os.path.join(parent_dir, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    # Create the temporary file path
    tmp_file_name = f"{container_name}-docker-compose.yaml"
    tmp_file_path = os.path.join(tmp_dir, tmp_file_name)

    compose_variables = {'lab_id': lab_id,
                         'student_id': student_id,
                         'container_name': container_name,
                         'domain': domain}

    # The subdomain_routes are a mapping of subdomains to port variables. This is used to create nginx server blocks.
    # The subdomain route key "main" is used to mean no subdomain.

    subdomain_routes = lab_config.get('subdomain_routes', {})

    available_ports = get_available_ports(8000, 9000, len(subdomain_routes), exclude=nginx.get_in_use_ports())

    # cache subdomain to port mapping. Ports will be assigned from available ports.
    subdomain_port_mapping = {}

    # create a mapping of subdomains to ports and add variables to the compose variables with the port numbers.
    for subdomain, port_variable in subdomain_routes.items():
        port = available_ports.pop()
        subdomain_port_mapping[subdomain] = port
        compose_variables[port_variable] = port

    compose_config_string = template.render(**compose_variables)
    compose_config = yaml.safe_load(compose_config_string)

    with open(tmp_file_path, 'w') as file:
        yaml.dump(compose_config, file)

    # old way:
    # os.system(f"docker-compose -p {container_name} -f {tmp_file_path} up -d")
    # use subprocess instead of os.system and wait for a response
    result = subprocess.run(f"docker-compose -p {container_name} -f {tmp_file_path} up -d", shell=True, check=True)
    if result.returncode != 0:
        raise ValueError("Error creating container.")

    # add nginx server blocks for each subdomain
    # signature for add_server is: add_server(self, student_id, lab_id, subdomain, domain, target_port)
    for subdomain, port in subdomain_port_mapping.items():
        nginx.add_server(student_id, lab_id, subdomain, domain, port, features=lab_config.get('features', {}))

    if save:
        nginx.save()
    nginx.reload(norestart=norestart)


def find_lab_config(lab_id):
    # find the lab config for the specified lab_id
    lab_config = None
    for lab in config['labs']:
        if lab['name'] == lab_id:
            lab_config = lab
            break
    if lab_config is None:
        raise ValueError(f"Could not find lab with id {lab_id}")
    return lab_config


def multi_create_student_container(student_id, lab_id, count, start=1, norestart=False):
    for idx in range(start, start + count):
        student_id_current = f"{student_id}{idx}"
        create_student_container(student_id_current, lab_id, norestart=True, save=False)  # don't restart while looping.
    nginx.save()
    nginx.reload(norestart=norestart)


# deletes student lab containers. If student_id is '*', all containers for the lab are deleted. If lab_id is '*',
# all containers for the student are deleted.
def delete_student_container(student_id, lab_id, norestart=False):
    servers_to_delete = []
    unique_containers_to_delete = set()  # Track unique containers
    for server in nginx.servers:
        try:
            # check if the server matches the student_id and lab_id, use fnmatch for wildcard support
            if fnmatch(server.student_id, student_id):  # Updated condition
                if fnmatch(server.lab_id, lab_id):  # Updated condition
                    servers_to_delete.append(server)
                    unique_containers_to_delete.add(f"{server.student_id}-{server.lab_id}")  # Add to unique container set
        except IndexError:
            # Skip server if it doesn't have the expected naming format
            continue

    for server in servers_to_delete:
        nginx.remove_server(server.name)

    for container_name in unique_containers_to_delete:

        # Get the directory where compose.py is located
        compose_dir = os.path.dirname(os.path.abspath(__file__))

        # Get the parent directory of the compose directory
        parent_dir = os.path.dirname(compose_dir)

        # Create the tmp directory inside the parent directory if it doesn't exist
        tmp_dir = os.path.join(parent_dir, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)

        # Create the temporary file path
        tmp_file_name = f"{container_name}-docker-compose.yaml"
        tmp_file_path = os.path.join(tmp_dir, tmp_file_name)
        print(f"Stopping and removing container {container_name}")

        delete_command = f"docker-compose -p {container_name} -f {tmp_file_path} down"

        # old way:
        # exit_code = os.system(delete_command)
        # use subprocess instead of os.system and wait for a response
        result = subprocess.run(delete_command, shell=True, check=True)

        if result.returncode != 0:
            print(f"Failed to stop and remove container {container_name} while running command: {delete_command}")
        elif os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

    nginx.save()
    nginx.reload(norestart=norestart)


def list_available_labs():
    lab_configs_path = 'lab_configs'
    labs = [f[:-5] for f in os.listdir(lab_configs_path) if f.endswith('.yaml')]
    return labs


def list_student_lab_combinations():
    containers = client.containers.list(all=True, filters={"label": "lab_id"})
    combinations = {}

    for container in containers:
        lab_id = container.labels.get('lab_id')
        student_id = container.labels.get('student_id')

        if lab_id and student_id:
            if lab_id not in combinations:
                combinations[lab_id] = []
            combinations[lab_id].append(student_id)

    return combinations
