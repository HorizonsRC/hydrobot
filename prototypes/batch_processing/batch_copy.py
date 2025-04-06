"""Copies files from template into site folders for batch processing."""

import os
import shutil

import pandas as pd
import ruamel.yaml

import hydrobot.config.horizons_source as source

# file locations
template_base = ".\\template\\"
destination_base = ".\\output_dump\\"
site_config = pd.read_csv("batch_config.csv")
annalist = "analyst_name"
batch_no = "XXX"
dsn_name = "batch_dsn.dsn"
batch_name = "batch_runner.bat"

run_files = []
dsn_file_list = []

# for each site
for site_index in site_config.index:
    site_code = source.find_three_letter_code(site_config.loc[site_index].site_name)
    # find base files
    base_files_to_copy = [
        os.path.join(template_base, f)
        for f in os.listdir(template_base)
        if os.path.isfile(os.path.join(template_base, f))
    ]
    # for each measurement at the site
    for measurement in site_config.loc[site_index].list_of_measurements.split(";"):
        # find measurement specific files
        files_to_copy = base_files_to_copy + [
            os.path.join(template_base, measurement, f)
            for f in os.listdir(os.path.join(template_base, measurement))
            if os.path.isfile(os.path.join(template_base, measurement, f))
        ]

        site_destination = os.path.join(
            destination_base,
            measurement,
            site_config.loc[site_index].site_name,
            batch_no,
        )
        # make sure it exists
        os.makedirs(site_destination, exist_ok=True)
        # copy files over
        for file in files_to_copy:
            shutil.copy2(file, site_destination)

        for file in os.listdir(site_destination):
            file = os.path.join(site_destination, file)
            ext = os.path.splitext(file)[-1].lower()

            if ext in [".hts", ".accdb"]:
                # rename files
                path, file_suffix = os.path.split(file)
                new_file_name = "_".join([batch_no, site_code, file_suffix])
                os.rename(file, os.path.join(path, new_file_name))

            if ext in [".yaml"]:
                # add in relevant info

                yaml = ruamel.yaml.YAML()
                with open(file) as fp:
                    data = yaml.load(fp)
                    data["site"] = site_config.loc[site_index].site_name
                    data["from_date"] = site_config.loc[site_index].from_date
                    data["to_date"] = site_config.loc[site_index].to_date
                    data["frequency"] = site_config.loc[site_index].frequency
                    data["analyst_name"] = annalist
                    dsn_file_list.append(
                        os.path.join(site_destination, data["export_file_name"])
                    )

                with open(file, "w") as fp:
                    yaml.dump(
                        {
                            key: (value if not pd.isna(value) else None)
                            for key, value in zip(
                                data.keys(), data.values(), strict=True
                            )
                        },
                        fp,
                    )

            if ext in [".py"]:
                # prep for running
                run_files += [file]


def remove_prefix_dots(string):
    """Removes any "."s at the start of a string."""
    if len(string) == 0:
        return string
    elif string[0] == ".":
        return remove_prefix_dots(string[1:])
    else:
        return string


def make_dsn(file_list, file_path, sub_dsn_number=0):
    """Makes the hilltop dsn."""
    if sub_dsn_number == 0:
        dsn_name = file_path
    else:
        dsn_name = file_path.split("\\")
        dsn_name[-1] = f"sub{sub_dsn_number}_{dsn_name[-1]}"
        dsn_name = "\\".join(dsn_name)
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
            next_file = file_path.split("\\")
            next_file[-1] = f"sub{sub_dsn_number}_{next_file[-1]}"
            next_file = "\\".join(next_file)
            next_file = os.path.abspath(next_file)
            dsn.write(f'File20="{next_file}"\n')
        make_dsn(file_list[19:], file_path, sub_dsn_number)


def make_batch(file_list, file_path):
    """Makes run script."""
    with open(file_path, "w") as runner:
        for file_name in file_list:
            runner.write(f'pushd "{os.path.abspath(os.path.split(file_name)[0])}"\n')
            runner.write("dir\n")
            runner.write(f'start python ".\\{os.path.split(file_name)[1]}"\n')


def make_blank_files(file_list):
    """Make blank .xml files so that the dsn still reads when a script fails."""
    for f in file_list:
        with open(f, "x") as _:
            pass


make_dsn(dsn_file_list, os.path.join(destination_base, dsn_name))
make_blank_files(dsn_file_list)
make_batch(run_files, os.path.join(destination_base, batch_name))
