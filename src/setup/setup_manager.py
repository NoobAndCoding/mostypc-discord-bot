import nextcord
from json import loads
from pathlib import Path
from dotenv import load_dotenv
from yaml import load

config_env = load_dotenv("src/setup/.env")
config_json = None
