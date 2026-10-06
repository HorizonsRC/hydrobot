"""Initialise hydrobot objects."""

import yaml

import hydrobot.data_sources as data_sources
import hydrobot.do_processor as do_processor
import hydrobot.processor as base_processor
import hydrobot.rf_processor as rf_processor
from hydrobot.providers.horizons import HorizonsProvider, HorizonsProviderConfig

DATA_FAMILY_DICT = data_sources.DATA_FAMILY_DICT

def build_provider(config):
    if config.provider == "horizons":
        provider_config = HorizonsProviderConfig(
            **config.provider_params
        )
        return HorizonsProvider(provider_config)

    raise ValueError(
        f"Unknown data provider: {config.provider}"
    )

def build_processor(config, provider):

    if "data_family" not in config:
        raise KeyError(
            "Attempted to create Hydrobot processor from config, "
            "but required key 'data_family' was "
            f"missing. Available keys are: {config.keys()}"
        )
    family = config["data_family"]
    #TODO
    if family not in DATA_FAMILY_DICT:
        raise KeyError(
            "Attempted to create Hydrobot processor from config, "
            f"but 'data_family' was set to {family} which is not recognised. "
            f"Available families are: {DATA_FAMILY_DICT.keys()}"
        )

    match family:
        case "dissolved_oxygen":
            processor_family = do_processor.DOProcessor
        case "rainfall":
            processor_family = rf_processor.RFProcessor
        case _:
            processor_family = base_processor.Processor

    return processor_family.from_config(config)


def initialise_from_yaml(yaml_path: str):
    """
    Initialise the appropriate Processor object for the given yaml file.

    Parameters
    ----------
    yaml_path : str
        Path to the yaml file

    Returns
    -------
    Processor
        Returns the Processor appropriate to the Data_Family
    """
    with open(yaml_path) as yaml_file:
        config = yaml.safe_load(yaml_file)

    provider_name = config["provider"]

    if provider_name not in ["horizons"]:
        raise KeyError(
            f"Unknown provider {provider_name}"
        )

    # auditor = build_auditor???

    provider = build_provider(config)

    processor = build_processor(config, provider)



