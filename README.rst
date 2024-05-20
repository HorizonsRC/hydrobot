======================
Hydrobot
======================


.. image:: https://img.shields.io/pypi/v/hydrobot.svg
        :target: https://pypi.python.org/pypi/hydrobot

.. image:: https://readthedocs.org/projects/hydrobot/badge/?version=latest
        :target: https://hydrobot.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

Python Package providing a suite of processing tools and utilities for Hilltop hydrological data.


* Free software: GNU General Public License v3
* Documentation: https://hydrobot.readthedocs.io.


Features
--------

* Processes data downloaded from Hilltop Server
* Uses annalist to record all changes to data
* Capable of various automated processing techniques, including:

  * Clipping data
  * Removing spikes based on FBEWMA smoothing
  * Identifying and removing 'flatlining' data, where an instrument repeats it's last collected data point (NOTE: It's unclear if this actually happening.)
  * Identifying gaps and gap lengths and closing small gaps
  * Aggregating check data from various sources.
  * Quality coding data based on NEMS standards

* Plotting data, including:

  * Processed data with quality codes
  * Comparing raw data to processed data
  * Showing all changes to the data
  * Visualizing check points from various sources.

Usage (Alpha)
-------------

The Alpha release of Hydrobot supports a "hybrid" workflow. This means that some external tools are still required to do a full processing. Importantly, the hybrid workflow relies on some R scripts to obtain check data from sources other than Hilltop. Further processing using Hilltop manager is also supported.

NOTE: Hydrobot 0.6.1 supports only Water Temperature processing at the moment, but more measurements will be supported in patches as the processing progresses.

Initial Setup (Repeat for each release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Install a Python 3.11 interpreter. Note that 3.12 is not supported just yet.
#. In your favourite shell, create a new virtual environment using this python interpreter and name it "hydrobot0.6.1". It's important that this is stored somewhere locally. I suggest creating a folder for virtual environments in your home folder::

    python -m venv path/to/venv/hydrobot0.6.1/

#. Activate this virtual environment. In powershell this should be something like::

    ./path/to/venv/hydrobot0.6.1/Scripts/Activate.ps1

#. If you're sure your venv is active (ensure with `which python` and confirm that you're using the interpreter in your venv folder), install the latest version of Hydrobot using pip::

    pip install hydrobot

#. Record which version of dependencies you have installed. The following pip freeze records which dependencies are
installed by the hydrobot install process for if auditing/reprocessing is required later::

    pip freeze > dependencies.txt

#. Navigate to the processing folder that you create as part of the Processing Steps below::

    cd //ares/hydro/processing/whatever/watertemp/site/30X/


Processing Steps
^^^^^^^^^^^^^^^^

#. Open Logsheet Loader. Fill it as normal, and note the start date of your processing period (i.e. end date of the previous period).
#. Navigate to the data source and site folder, and create your processing folder.
#. Copy all the processing files in this folder into your processing folder::

    \\ares\Environmental Data Validation\Water Temperature\Documents\Hydrobot_0.6.1_Files\

    //ares/Environmental\ Data\ Validation/Water\ Temperature/Documents/Hydrobot_0.6.1_Files/

#. In your processing folder, open the `config.yaml` file and change the fields `site`, `from_date`, `to_date`, `analyst_name`. Feel free to mess with the other values once you get the hang of it. No one will die.

#. Run the R script. I'm not an R guy so I'm not sure how to do this other than to open it in R studio, highlighting all the code, and hitting `Ctrl+Enter`. This should create a bunch of `.csv` files containing the check data from various sources. This is a good reasource for perusal during processing, but will be imbibed by hydrobot to for QC encoding.

#. Make sure your virtual environment is set up and active. Ensure with `which python` and confirm that your python interpreter is running from your venv folder.

#. Run the hydrobot processing script::

    python processing_script.py

#. If all goes well, the processing script will open a browser tab showing a diagnostic dash for your site. Use this to identify issues in the site.

#. Use your python skills to solve some issues, like removing erroneous check data points or deleting chunks of data. More extensive documentation on actually using hydrobot will follow in future releases.

#. Open the resulting processed.xml in manager, and copy it over to a hts file.

#. Open the WaterTemp_check_data.csv outputed from the R file in a spreadsheet (sorry) and copy into hts file.

#. Happy processing!

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template. Furthermore,
Sam is a real champ with the coding and whatnot. Thanks Sam.

Aww thanks Nic. You also da man <3

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
