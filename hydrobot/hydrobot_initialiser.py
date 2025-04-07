"""Initialise hydrobot objects."""

import yaml

import hydrobot.data_sources as data_sources
import hydrobot.do_processor as do_processor
import hydrobot.processor as base_processor
import hydrobot.rf_processor as rf_processor

DATA_FAMILY_DICT = data_sources.DATA_FAMILY_DICT


def initialise_hydrobot_from_yaml(yaml_path: str):
    """
    Initialises the appropriate Processor object for the given yaml file.

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
    if "DATA_FAMILY" not in processing_parameters:
        raise KeyError(
            f"Attempted to create Hydrobot processor from {yaml_path}, but required key 'DATA_FAMILY' was "
            f"missing. Available keys are: {processing_parameters.keys()}"
        )
    family = processing_parameters["DATA_FAMILY"]
    if family not in DATA_FAMILY_DICT:
        raise KeyError(
            f"Attempted to create Hydrobot processor from {yaml_path}, but 'DATA_FAMILY' was set to {family} "
            f"which is not recognised. Available families are: {DATA_FAMILY_DICT.keys()}"
        )

    match family:
        case "Dissolved Oxygen":
            processor_family = do_processor.DOProcessor
        case "TwoLevel":
            processor_family = rf_processor.RFProcessor
        case _:
            processor_family = base_processor.Processor

    return processor_family.from_processing_parameters_dict(processing_parameters)
