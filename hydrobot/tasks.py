"""Tasks to be completed for mass processing."""

import csv
import importlib.resources as pkg_resources
import os
import platform
import re
import shutil
from datetime import datetime

import ruamel.yaml

import hydrobot.data_sources as data_sources
import hydrobot.utils as utils


def _get_minimum_batch_number():
    """
    Return minimum allowed batch number.

    Returns
    -------
    int
    """
    return 401


def _get_template(data_family):
    """
    Get the data_family template path.

    Parameters
    ----------
    data_family : str
        Which data family to look for.
        Corresponds to the directories in hydrobot/config/template_families

    Returns
    -------
    pathlib.Path
    """
    directory = pkg_resources.files("hydrobot.config.template_families").joinpath(
        data_family
    )
    if not directory.is_dir():
        raise ValueError(f"Data family not found. No resource at {directory}")
    return directory


def _get_generic_template():
    """
    Get the generic template path.

    Returns
    -------
    pathlib.Path
    """
    return pkg_resources.files("hydrobot.config.generic_template")


def copy_data_family_template(data_family: str, destination_path: str):
    """
    Copy the template files into a destination directory.

    Parameters
    ----------
    data_family : str
        Which data family to look for.
        Corresponds to the directories in hydrobot/config/template_families
    destination_path : str
        The upper bound for clipping, by default None.
        If None, the high clip value from the class defaults is used.

    Returns
    -------
    None
    """
    for resource in _get_template(data_family).iterdir():
        if os.path.isfile(resource):
            shutil.copy(resource, destination_path)

    for resource in _get_generic_template().iterdir():
        if os.path.isfile(resource):
            shutil.copy(resource, destination_path)


def _remove_non_numeric_from_string(string: str):
    """
    Take a string that has a mix of numeric and non-numeric characters.

    Returns only numeric.

    e.g. "!@#123abc456ABC" gets turned into "123456".

    Parameters
    ----------
    string : str

    Returns
    -------
    str

    """
    return re.sub(r"\D", "", string)


def find_next_batch_number(directory: str, minimum: int = _get_minimum_batch_number()):
    """
    Find the highest value among subdirectories and adds 1.

    Parameters
    ----------
    directory : str
        path to directory to look for subdirectories in
    minimum : int
        Returned value is at least this.

    Returns
    -------
    int
        latest batch number, or 0 if there is no numeric subdirectories
    """
    sub_dirs = [
        i
        for i in os.listdir(directory)
        if (
            i == _remove_non_numeric_from_string(i)
            and os.path.isdir(os.path.join(directory, i))
        )
    ]
    sub_dirs = [int(i) for i in sub_dirs if i]  # removes empty strings
    sub_dirs.append(minimum - 1)
    return max(sub_dirs) + 1


def find_single_file_by_ext(directory, ext):
    """
    Find .ext file in the directory if only one exists with that extension.

    Parameters
    ----------
    directory
        path to directory which contains ext file
    ext
        extension to be checked

    Returns
    -------
    str
        path to the ext file

    Raises
    ------
    FileNotFoundError
        If the directory has no .ext file in it
    FileExistsError
        If the directory has multiple .ext files in it

    """
    files = [
        i for i in os.listdir(directory) if os.path.isfile(os.path.join(directory, i))
    ]
    found_file = [i for i in files if i.split(".")[-1] == ext]

    match len(found_file):
        case 0:
            raise FileNotFoundError(
                f"No .{ext} found from template at '{directory}'."
                f"All available files are: {files}"
            )
        case 1:
            return os.path.join(directory, found_file[0])
        case _:
            raise FileExistsError(
                f"Multiple .{ext} files found from template at '{directory}'."
                f"Available .{ext} files are: {found_file}"
            )


def modify_data_template(target_dir, site, from_date=None, **kwargs):
    """
    Modify a copied data template.

    Parameters
    ----------
    target_dir
    site
    from_date
    kwargs

    Returns
    -------
    str
        export file name

    Raises
    ------
    FileNotFoundError
        If the directory has no .yaml file in it
    FileExistsError
        If the directory has multiple .yaml files in it
    """
    yaml_file = find_single_file_by_ext(target_dir, "yaml")
    yaml = ruamel.yaml.YAML()
    with open(yaml_file) as fp:
        data = yaml.load(fp)
        data["site"] = site
        for key, value in kwargs.items():
            data[key] = value
        if "depth" in data and data["depth"] is not None:
            name = data_sources.depth_standard_measurement_name_by_data_family(
                data["data_family"], data["depth"]
            )
            data["standard_measurement_name"] = name
            data["archive_standard_measurement_name"] = name
        if "archive_standard_measurement_name" not in data:
            data["archive_standard_measurement_name"] = data[
                "standard_measurement_name"
            ]
        if from_date is None:
            try:
                last_time = utils.find_last_time(
                    base_url=data["base_url"],
                    hts=data["archive_standard_hts_filename"],
                    site=site,
                    measurement=data["archive_standard_measurement_name"],
                )
                data["from_date"] = last_time.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                data["from_date"] = None
        else:
            data["from_date"] = from_date
    with open(yaml_file, "w") as fp:
        yaml.dump(data, fp)
    return data["export_file_name"]


def create_single_hydrobot_batch(
    base_dir,
    site,
    data_family,
    from_date=None,
    batch_no=None,
    create_directory=False,
    depth=None,
    **kwargs,
):
    """
    Create a single hydrobot run.

    Parameters
    ----------
    base_dir : str
        where the batch is created.
    site : str
        site name.
    data_family : str
        what kind of measurement is to be processed.
    from_date : str, optional
        from date, will use latest available data if absent, will fail if no latest
        data available.
    batch_no: str, optional
        batch number, will find batch number from base_dir if absent.
    create_directory: bool, optional
        whether to create directories if missing. Default false, so will raise error if
        directory missing
    depth: str or None, optional
        Added to end of path if it exists. None for non-depth sites.
    kwargs : dict, optional
        any parameters to add to config_yaml for batch.

    Returns
    -------
    target_dir : str
        where the new run will be created.
    output_filename : str
        path to where the output of the hydrobot run is expected.
    """
    if batch_no is None:
        try:
            batch_no = find_next_batch_number(
                directory=str(os.path.join(base_dir, site))
            )
        except FileNotFoundError as e:
            if create_directory:
                batch_no = _get_minimum_batch_number()
            else:
                raise e
    target_dir = [base_dir, site, str(batch_no)]
    if depth is not None:
        depth_unit = data_sources.DATA_FAMILY_DICT[data_family]["depth_unit"]
        target_dir.append(str(depth) + depth_unit)
        kwargs["depth"] = int(depth)
    target_dir = str(os.path.join(*target_dir))
    os.makedirs(target_dir, exist_ok=False)
    copy_data_family_template(data_family=data_family, destination_path=target_dir)
    output_filename = modify_data_template(target_dir, site, from_date, **kwargs)

    return target_dir, output_filename


def create_mass_hydrobot_batches(
    home_dir: str, base_dir: str, dict_list: [dict], create_directory=False
):
    """
    Create many hydrobot batches via create_single_hydrobot_batch.

    Parameters
    ----------
    home_dir : str
        Path to where run file and dsn file will be created.
    base_dir : str
        Where batches should be located.
    dict_list : dict
        Parameters to be used for each batch. Must contain "site" and "data_family" as
        keys.
    create_directory: bool, optional
        whether to create directories if missing. Default false, so will raise error if
        directory missing

    Returns
    -------
    None
        creates many files
    """
    hydrobot_scripts = []
    hydrobot_outputs = []
    if not os.path.isdir(home_dir):
        if create_directory:
            os.makedirs(home_dir)
        else:
            raise NotADirectoryError(
                f"No home directory, check path or create directory at at {home_dir}"
            )
    for run in dict_list:
        target_dir, output_filename = create_single_hydrobot_batch(
            base_dir, **run, create_directory=create_directory
        )
        hydrobot_scripts.append(find_single_file_by_ext(target_dir, "py"))
        hydrobot_outputs.append(str(os.path.join(target_dir, output_filename)))

    make_dsn(hydrobot_outputs, os.path.join(home_dir, "hydrobot_dsn.dsn"))
    make_blank_files(hydrobot_outputs)
    if platform.system() == "Linux":
        make_bash(hydrobot_scripts, os.path.join(home_dir, "run_hydrobot.sh"))
    elif platform.system() == "Windows":
        make_batch(hydrobot_scripts, os.path.join(home_dir, "run_hydrobot.bat"))
    else:
        raise OSError("Unsupported operating system for run script creation.")


def make_dsn(file_list, file_path, sub_dsn_number=0):
    """Make the hilltop dsn."""
    path_sep = "\\"
    if sub_dsn_number == 0:
        dsn_name = file_path
    else:
        dsn_name = file_path.split(path_sep)
        dsn_name[-1] = f"sub{sub_dsn_number}_{dsn_name[-1]}"
        dsn_name = path_sep.join(dsn_name)
    if len(file_list) <= 20:  # hilltop dsn max files is 20
        with open(dsn_name, "w") as dsn:
            dsn.write("[Hilltop]\n")
            dsn.write("Style=Merge\n")
            for index, file_name in enumerate(file_list):
                dsn.write(f'File{index + 1}="{os.path.abspath(file_name)}"\n')
    else:  # chaining dsns together
        sub_dsn_number += 1
        with open(dsn_name, "w") as dsn:
            dsn.write("[Hilltop]\n")
            dsn.write("Style=Merge\n")
            for index, file_name in enumerate(file_list[:19]):
                dsn.write(f'File{index + 1}="{os.path.abspath(file_name)}"\n')
            next_file = file_path.split(path_sep)
            next_file[-1] = f"sub{sub_dsn_number}_{next_file[-1]}"
            next_file = path_sep.join(next_file)
            next_file = os.path.abspath(next_file)
            dsn.write(f'File20="{next_file}"\n')
        make_dsn(file_list[19:], file_path, sub_dsn_number)


def make_batch(file_list, file_path):
    """Make run script for Windows."""
    with open(file_path, "w") as runner:
        for file_name in file_list:
            runner.write(f'pushd "{os.path.abspath(os.path.split(file_name)[0])}"\n')
            runner.write("dir\n")
            runner.write(f'start python ".\\{os.path.split(file_name)[1]}"\n')


def make_bash(file_list, file_path):
    """Make run script for Linux."""
    with open(file_path, "w") as runner:
        for file_name in file_list:
            runner.write(f'cd "{os.path.abspath(os.path.split(file_name)[0])}"\n')
            runner.write("ls\n")
            runner.write(f'python "./{os.path.split(file_name)[1]}" &\n')


def make_blank_files(file_list):
    """Make blank .xml files so that the dsn still reads when a script fails."""
    for f in file_list:
        with open(f, "x") as _:
            pass


def csv_to_batch_dicts(file_path):
    """
    Obtain a list of dicts from csv.

    Parameters
    ----------
    file_path : str
        path to the csv

    Returns
    -------
    [dict]
    """
    title_row = []
    list_of_dicts = []
    with open(file_path, newline="") as file:
        reader = csv.reader(file, delimiter=",", quotechar="|")
        for row in reader:
            if not title_row:
                title_row = row
            else:
                if row[1] != "":
                    row[1] = datetime.strptime(row[1], "%d/%m/%Y %H:%M").strftime(
                        "%Y-%m-%d %H:%M"
                    )
                if row[2] != "":
                    row[2] = datetime.strptime(row[2], "%d/%m/%Y %H:%M").strftime(
                        "%Y-%m-%d %H:%M"
                    )
                zipper = zip(title_row, row, strict=True)
                list_of_dicts.append({k: v for (k, v) in zipper if v})
    return list_of_dicts


def create_depth_hydrobot_batches(
    home_dir, base_dir, dict_list, create_directory=False
):
    """
    Create hydrobot batches with depth profiles via create_single_hydrobot_batch.

    Parameters
    ----------
    home_dir : str
        Path to where run file and dsn file will be created.
    base_dir : str
        Where batches should be located.
    dict_list : dict
        Parameters to be used for each batch. Must contain "site", "data_family",
        and "depth" as keys. Depths are in mm and separated by semicolons.
    create_directory: bool, optional
        whether to create directories if missing. Default false, so will raise error
        if directory missing

    Returns
    -------
    None
        creates many files
    """
    hydrobot_scripts = []
    hydrobot_outputs = []
    if not os.path.isdir(home_dir):
        if create_directory:
            os.makedirs(home_dir)
        else:
            raise NotADirectoryError(
                f"No home directory, check path or create directory at at {home_dir}"
            )
    for run in dict_list:
        if "depths" not in run:
            raise KeyError("Missing key 'depths'")
        site_directory = str(os.path.join(base_dir, run["site"]))
        if not os.path.isdir(site_directory):
            if create_directory:
                os.makedirs(site_directory)
            else:
                raise NotADirectoryError(
                    f"No directory for site '{run['site']}', check spelling or"
                    f"create directory at at {site_directory}"
                )
        batch_no = str(find_next_batch_number(directory=site_directory))
        depths = run.pop("depths").split(";")
        for depth in depths:
            target_dir, output_filename = create_single_hydrobot_batch(
                base_dir,
                **run,
                depth=depth,
                create_directory=create_directory,
                batch_no=batch_no,
            )
            hydrobot_scripts.append(find_single_file_by_ext(target_dir, "py"))
            hydrobot_outputs.append(str(os.path.join(target_dir, output_filename)))

    make_dsn(hydrobot_outputs, os.path.join(home_dir, "hydrobot_dsn.dsn"))
    make_blank_files(hydrobot_outputs)
    if platform.system() == "Linux":
        make_bash(hydrobot_scripts, os.path.join(home_dir, "run_hydrobot.sh"))
    elif platform.system() == "Windows":
        make_batch(hydrobot_scripts, os.path.join(home_dir, "run_hydrobot.bat"))
    else:
        raise OSError("Unsupported operating system for run script creation.")
