======================
Hydrobot
======================


.. image:: https://img.shields.io/pypi/v/hydrobot.svg
        :target: https://pypi.python.org/pypi/hydrobot

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. image:: https://readthedocs.org/projects/hydrobot/badge/?version=latest
        :target: https://hydrobot.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

Python Package providing a suite of processing tools and utilities for Hilltop
hydrological data.


* Free software: GNU General Public License v3
* Documentation: https://hydrobot.readthedocs.io.


Features
--------

* Processes data downloaded from Hilltop Server
* Uses annalist to record all changes to data
* Capable of various automated processing techniques, including:

  * Clipping data
  * Removing spikes based on FBEWMA smoothing
  * Identifying and removing 'flatlining' data, where an instrument repeats
    it's last collected data point (NOTE: It's unclear if this actually
    happening.)
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

The Alpha release of Hydrobot supports a "hybrid" workflow. This means that
some external tools are still required to do a full processing. Importantly,
the hybrid workflow relies on some R scripts to obtain check data from sources
other than Hilltop. Further processing using Hilltop manager is also supported.

NOTE: Hydrobot 0.9.5 does not support all NEMs data sources currently,
but more measurements will be supported in patches as the processing
progresses.

Initial Setup (Repeat for each release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Install a Python 3.11 interpreter (3.12 is not supported just yet).

#. In your favourite shell (if you don't know what that is, use powershell -
   it's already installed on windows), create a new virtual environment using
   this python interpreter and name it "hydrobot0.9.5". It's important that
   this is stored somewhere locally. For example, it could be stored in a
   "Hydrobot" folder in the C: drive, which would need the command::

    python -m venv C:/Hydrobot/hydrobot0.9.5/
    cd C:/Hydrobot/hydrobot0.9.5/

#. Activate this virtual environment. In powershell this should be something
   like::

    C:/Hydrobot/hydrobot0.9.5/Scripts/Activate.ps1

#. With your venv active, install the latest version of Hydrobot using pip::

    pip install hydrobot

#. Record which version of dependencies you have installed. The following pip
   freeze records which dependencies are installed by the hydrobot install
   process for if auditing/reprocessing is required later::

    pip freeze > dependencies.txt


Manual Processing Steps
^^^^^^^^^^^^^^^^^^^^^^^
For processing one particular site:

#. Open Logsheet Loader. Fill it as normal, and note the start date of your
   processing period (i.e. end date of the previous period).

#. Navigate to the data source and site folder, and create your batch folder.

#. Copy all the hydrobot processing template files from the documents folder
   into your new batch folder, then rename with batch number and location code.
   The location of e.g. the water temperature template is::

    \\ares\Environmental Data Validation\Water Temperature\Documents\Hydrobot_template\

#. In your processing folder, open the `config.yaml` file and fill the fields
   `site`, `from_date`, `to_date`, `analyst_name`. Adjust the other values if
   desired - default values should work for most situations, but each site can
   have it's own idiosyncrasies.

#. Run the R script. I'm not an R guy so I'm not sure how to do this other than
   to open it in R studio, highlighting all the code, and hitting `Ctrl+Enter`.
   This should create a bunch of `.csv` files containing the check data from
   various sources. This is a good resource for perusal during processing, but
   will be imbibed by hydrobot to for QC encoding.

#. Make sure your virtual environment is set up (see initial setup
   instructions) and activate it. To activate, in your shell type the location
   of the "Activate.ps1" script in the venv/Scripts folder, e.g.::

    C:/Hydrobot/hydrobot0.9.5/Scripts/Activate.ps1

   You can ensure it is active by typing `gcm python` and confirm that your
   python interpreter (under "Source") is running from your venv folder.

#. Navigate to your batch folder in your shell. To navigate to the batch
   folder, use the following "cd" command with your specific details::

    cd "\\ares\Environmental Data Validation\measurement\site\batch\"

   e.g. if you are doing water temperature for teachers college in batch 400,
   your cd command would be::

    cd "\\ares\Environmental Data Validation\Water Temperature\Manawatu at Teachers College\400"

#. Run the hydrobot processing script using streamlit (name changes slightly by
   data source)::

    streamlit run wt_script.py

#. If all goes well, the processing script will open a browser tab showing a
   diagnostic dash for your site. Use this to identify issues in the site.

#. Optionally, modify the python script to solve some issues, like removing
   erroneous check data points or deleting chunks of data, then rerun the
   script.

#. Open the resulting processed.xml in manager, and copy it over to the hts
   file found in the batch folder.

#. Modify the data in hilltop as needed

#. Open the WaterTemp_check_data.csv output by the R file in a spreadsheet and
   copy into the hts batch file.

#. Copy to provisional automation when complete.

Batch Processing Steps
^^^^^^^^^^^^^^^^^^^^^^
For processing many sites at once

#. For each measurement you are processing, copy the script and yaml into a
   directory named after the measurement

#. Fill in the batch_config.csv with the sites that are to be processed
   (to_date and frequency can be ommitted, which will be inferred)

#. Run the batch_copy.py script

#. Run the batch_runner.bat



HURL Schemas - YAML-Style Pydantic Models
-----------------------------------------

Hydrobot includes a new `hurl.schemas` module that provides Pydantic models with YAML-style string representations. These models use a `ModelReprMixin` that formats the output in a readable, hierarchical YAML format.

Features
^^^^^^^^

* **YAML-style output**: All models produce clean, indented YAML representations
* **Excludes unset values**: Only shows fields that have been set (not None/unset)
* **Customizable always-include fields**: Specify fields to always show even if None
* **Recursive formatting**: Handles nested models and lists properly
* **Model name headers**: Each representation starts with the model class name

Usage Example
^^^^^^^^^^^^^

.. code-block:: python

    from hurl.schemas import DataItem, GetDataRequest, GetDataResponse

    # Create a data request
    request = GetDataRequest(
        site="TestSite",
        measurement="WaterLevel", 
        from_date="2023-01-01",
        to_date="2023-01-31"
    )
    
    print(request)
    # Output:
    # GetDataRequest:
    #   site: TestSite
    #   measurement: WaterLevel
    #   from_date: '2023-01-01'
    #   to_date: '2023-01-31'
    #   limit: null

    # Create data items and response
    data_items = [
        DataItem(id=1, value=3.14, tags=["foo", "bar"]),
        DataItem(id=2, value=2.71)
    ]
    
    response = GetDataResponse(
        status="success",
        data=data_items,
        total_count=100
    )
    
    print(response)
    # Output:
    # GetDataResponse:
    #   status: success
    #   data:
    #   - id: 1
    #     value: 3.14
    #     tags:
    #     - foo
    #     - bar
    #   - id: 2
    #     value: 2.71
    #   total_count: 100
    #   error_message: null

Creating Custom Models
^^^^^^^^^^^^^^^^^^^^^^

To create your own model with YAML-style representation:

.. code-block:: python

    from typing import Optional, ClassVar
    from pydantic import BaseModel, Field
    from hurl.schemas.base import ModelReprMixin

    class MyModel(ModelReprMixin, BaseModel):
        # Fields to always include even if None
        always_include_fields: ClassVar[set] = {"important_field"}
        
        name: str = Field(..., description="Model name")
        value: Optional[float] = Field(default=None, description="Optional value")
        important_field: Optional[str] = Field(default=None, description="Always shown")

Available Models
^^^^^^^^^^^^^^^^

* ``DataItem``: Represents individual data points with id, value, and optional tags
* ``GetDataRequest``: Request model for data retrieval with site, measurement, and date filters
* ``GetDataResponse``: Response model containing status, data items, and metadata


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template. Furthermore,
Sam is a real champ with the coding and whatnot. Thanks Sam.

Aww thanks Nic. You also da man <3

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
