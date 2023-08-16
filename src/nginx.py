import os

from dotenv import load_dotenv

from certificate_providers import NoneProvider, SelfSignedProvider

load_dotenv()

NGINX_CONF_DIR = os.environ.get('NGINX_CONF_DIR', '/etc/nginx/')
NGINX_CONFIG_PATH = os.path.join(os.path.dirname(NGINX_CONF_DIR), 'shogun.conf')

# Environment variable for selecting the certificate provider
CERT_PROVIDER_ENV = os.environ.get('CERT_PROVIDER', 'NONE').upper()

def load_certificate_provider():
    """
    Loads and returns the certificate provider based on the environment configuration.
    """
    if CERT_PROVIDER_ENV == 'NONE':
        return NoneProvider()
    elif CERT_PROVIDER_ENV == 'SELF_SIGNED':
        return SelfSignedProvider()
    else:
        raise ValueError(f"Unsupported certificate provider: {CERT_PROVIDER_ENV}")


class ShogunServer:
    def __init__(self, student_id, subdomain, lab_id, domain, target_ip, target_port, listen_ports=None):
        self.certificate_provider = load_certificate_provider()
        if listen_ports is None:
            # If no listen ports are specified, default to 80 and 443 if the NoneProvider is not used
            if not isinstance(self.certificate_provider, NoneProvider):
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
        # convert listen ports to strings
        self.listen_ports = [str(port) for port in listen_ports]


    # Generate a single metadata comment for simply parsing the config to retrieve the servers from the nginx config
    # The format will be "# METADATA:student_id|subdomain|lab_id|domain|target_ip|target_port|listen_ports"
    def _generate_metadata(self):
        # the ports are stored as strings and may include 'ssl' if the certificate provider is not NoneProvider.
        # For the metadata we need to remove the 'ssl' string so that it can be parsed as an integer
        listen_ports = ",".join([port.replace("ssl", "") for port in self.listen_ports])

        return f"# METADATA:{self.student_id}|{self.subdomain}|{self.lab_id}|{self.domain}|{self.target_ip}|{self.target_port}|{listen_ports}"

    # Class method to parse a metadata comment line and return a Server object
    # All parameters are strings except for listen_ports, which is a list of integers
    @classmethod
    def from_metadata(cls, metadata):
        metadata = metadata.replace("# METADATA:", "")
        metadata = metadata.split("|")
        return cls(metadata[0], metadata[1], metadata[2], metadata[3], metadata[4], metadata[5],
                   [int(port) for port in metadata[6].split(",")])

    def generate_raw_block(self):
        cert_path, key_path = self.certificate_provider.get_certificate_paths(self.lab_id)
        ssl_config = ""

        if "443" in self.listen_ports and not isinstance(self.certificate_provider, NoneProvider):
            ssl_config = f"""
    ssl_certificate     {cert_path};
    ssl_certificate_key {key_path};                
    ssl_prefer_server_ciphers off;
                """
            # append ssl to the 443 listen port (e.g. "listen 443 ssl;")
            self.listen_ports[self.listen_ports.index("443")] = f"443 ssl"

        listen_port_str = "\n".join(f"    listen {port};" for port in self.listen_ports)
        return f"""{self._generate_metadata()}
server {{
{ssl_config}
{listen_port_str}
    server_name {self.name};
    
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
