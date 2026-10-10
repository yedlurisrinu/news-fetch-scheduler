from pathlib import Path
from tomllib import load
"""General Static information"""

setting_config = {}

def get_setting(key:str):
    return setting_config[key]

def load_setting():
    global setting_config
    path = Path(__file__).parent.parent
    with open(file=str(path)+"/resources/app-config-settings.toml", mode='rb') as config:
        setting_config = load(config)
        
