import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


# Define a config class that will load the config from a yaml file and store it as a dictionary.
class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def __getitem__(self, item):
        return self.config[item]

    def __contains__(self, item):
        return item in self.config

    def __repr__(self):
        return f"Config({self.config})"


# Get the config object for this application. The config file is defined in the .env file as CONFIG_FILE. If no config
# file is defined, the default config file is relative to the project root at ./lab_config/default_config.yaml.


config_path = os.getenv('CONFIG_FILE', os.path.join(os.path.dirname(__file__), '../lab_configs/default_config.yaml'))
config = Config(config_path)
