import os

from dotenv import load_dotenv

load_dotenv()

NGINX_CONF_DIR = os.environ.get('NGINX_CONF_DIR', '/etc/nginx/')
NGINX_CONFIG_PATH = os.path.join(os.path.dirname(NGINX_CONF_DIR), 'shogun.conf')
USE_SSL = os.environ.get('USE_SSL') == 'true'
SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH')
SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH')


class ShogunServer:
    def __init__(self, student_id, subdomain, lab_id, domain, target_ip, target_port, listen_ports=None):
        if listen_ports is None:
            if USE_SSL:
                listen_ports = [443, 80]
            else:
                listen_ports = [80]
        self.name = f"{student_id}.{subdomain}.{lab_id}.{domain}" if subdomain != 'main' else f"{student_id}.{lab_id}.{domain}"
        self.student_id = student_id
        self.subdomain = subdomain
        self.lab_id = lab_id
        self.domain = domain
        self.target_ip = target_ip
        self.target_port = target_port
        self.listen_ports = listen_ports

    # Generate a single metadata comment line for simply parsing the config to retrieve the servers from the nginx config
    # The format will be "# METADATA:student_id|subdomain|lab_id|domain|target_ip|target_port|listen_ports"
    def _generate_metadata(self):
        return f"# METADATA:{self.student_id}|{self.subdomain}|{self.lab_id}|{self.domain}|{self.target_ip}|{self.target_port}|{','.join(str(port) for port in self.listen_ports)}"

    # Class method to parse a metadata comment line and return a Server object
    # All parameters are strings except for listen_ports, which is a list of integers
    @classmethod
    def from_metadata(cls, metadata):
        metadata = metadata.replace("# METADATA:", "")
        metadata = metadata.split("|")
        return cls(metadata[0], metadata[1], metadata[2], metadata[3], metadata[4], metadata[5],
                   [int(port) for port in metadata[6].split(",")])

    def generate_raw_block(self):
        ssl_str = ""
        if 443 in self.listen_ports and USE_SSL:
            ssl_str = f"""
                ssl_certificate     {SSL_CERT_PATH};
                ssl_certificate_key {SSL_KEY_PATH};
                ssl on;
                """

        listen_port_str = "\n".join(f"    listen {port};" for port in self.listen_ports)
        return f"""{self._generate_metadata()}
        server {{
{listen_port_str}
    server_name {self.name};
    {ssl_str}
    location / {{
        proxy_pass http://{self.target_ip}:{self.target_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}"""


class NginxConfig:
    servers: list[ShogunServer]

    def __init__(self, config_path=NGINX_CONFIG_PATH):
        self.config_path = config_path

        if not os.path.exists(config_path):
            with open(config_path, 'w') as file:
                file.write('')

        with open(config_path, 'r') as file:
            self.raw_config = file.read()

        # Skip comments at the beginning of the file if they don't contain "METADATA".
        if self.raw_config.startswith('#'):
            raw_config = self.raw_config.split('\n\n')
            raw_config = [block for block in raw_config if 'METADATA' in block]
            self.raw_config = '\n\n'.join(raw_config)

        self.servers = self._parse_servers

    # Using the metadata comments in the Server class and the _parse_metadata method, parse the raw config file into a
    # list of Server objects. Returns an empty list if there are no server blocks with metadata comments.
    @property
    def _parse_servers(self):
        servers: list[ShogunServer] = []
        raw_config = self.raw_config.split('\n\n')
        if not raw_config:
            return servers
        else:
            for block in raw_config:
                if block.startswith('# METADATA'):
                    metadata_line = block.split('\n')[0]
                    servers.append(ShogunServer.from_metadata(metadata_line))
            return servers

    def add_server(self, student_id, lab_id, subdomain, domain, target_port, listen_ports=None, target_ip='127.0.0.1'):
        new_server = ShogunServer(student_id, subdomain, lab_id, domain, target_ip, target_port, listen_ports)

        if not any(server.name == new_server.name for server in self.servers):
            self.servers.append(new_server)

    def remove_server(self, server_name):
        self.servers = [server for server in self.servers if server.name.strip() != server_name.strip()]

    def save(self):
        updated_config = '\n\n'.join([server.generate_raw_block() for server in self.servers])
        print(f"Saving nginx config to {self.config_path}.")

        with open(self.config_path, 'w') as file:
            file.write(updated_config)

    @staticmethod
    def reload(norestart=False):
        if norestart:
            print("Skipping nginx reload.")
            return
        else:
            print("Reloading nginx...")
            os.system('nginx -s reload')
