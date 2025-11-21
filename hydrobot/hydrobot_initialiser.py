"""Initialise hydrobot objects."""

import yaml

import hydrobot.data_sources as data_sources
import hydrobot.do_processor as do_processor
import hydrobot.processor as base_processor
import hydrobot.rf_processor as rf_processor

DATA_FAMILY_DICT = data_sources.DATA_FAMILY_DICT


def initialise_hydrobot_from_yaml(yaml_path: str):
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
        processing_parameters = yaml.safe_load(yaml_file)
    if "data_family" not in processing_parameters:
        raise KeyError(
            f"Attempted to create Hydrobot processor from {yaml_path}, "
            "but required key 'data_family' was "
            f"missing. Available keys are: {processing_parameters.keys()}"
        )
    family = processing_parameters["data_family"]
    if family not in DATA_FAMILY_DICT:
        raise KeyError(
            f"Attempted to create Hydrobot processor from {yaml_path}, "
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

    return processor_family.from_config_yaml(yaml_path)
