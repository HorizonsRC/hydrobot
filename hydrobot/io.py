import yaml

def read_yaml_config(yaml_path):
    with open(yaml_path) as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config
