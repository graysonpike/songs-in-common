import json


CONFIG = None


def load_config():
    global CONFIG
    file = open("config.json")
    CONFIG = json.load(file)


def get_config():
    global CONFIG
    if CONFIG == None:
        load_config()
    return CONFIG
