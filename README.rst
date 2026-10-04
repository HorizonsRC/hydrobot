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
======================

* Processes data downloaded from Hilltop Server
* Creates output files in a format appropriate for returning data to Hilltop
* Uses annalist to record changes to data generated from processing
* Capable of various automated processing techniques, including:

  * Clipping data
  * Removing spikes based on FBEWMA smoothing
  * Identifying and removing 'flatlining' data, where an instrument repeats
    it's last collected data point (NOTE: Low precision data may be falsely
    flagged by this)
  * Identifying gaps and gap lengths and closing small gaps
  * Aggregating check data from various sources
  * Collating comments + metadata from various inspections and related activities
  * Quality coding data based on NEMS standards

* Plotting data, including:

  * Processed data with quality codes
  * Comparing raw data to processed data
  * Showing all changes to the data
  * Visualizing check points from various sources

Usage (Alpha)
======================

Hydrobot supports a "hybrid" workflow. This means that a large number of sites
can be processed automatically, but if on examination an individual site has a
problem an adjustment can be applied before the data loaded. This is required
for environmental data as there are many various issues that the data can have.

To support this hybrid workflow, Hydrobot processes data on a "one site, one
script" basis. All the logic required for an individual site's processing is
contained in the script, with some supporting info in the yaml. Further data is
drawn from a Hilltop server when run (i.e. the data itself is gathered from the
server).

NOTE: Hydrobot 0.9.15 does not support all NEMS data sources currently,
but more measurements are planned to will be supported in later releases.

Installation (Repeat for each release)
---------------------------------------

#. Ensure you have a Python 3.11 interpreter installed (3.12+ is not supported)

#. In your favourite shell (if you don't know what that is, use powershell -
   it's already installed on windows), create a new virtual environment using
   this python interpreter and name it "hydrobot0.9.15". It's important that
   this is stored somewhere locally. Assuming it is stored in a "Hydrobot"
   folder in the C: drive, use the command::

    py -3.11 -m venv C:/Hydrobot/hydrobot0.9.15/

#. Activate this virtual environment. In powershell this should be something
   like::

    C:/Hydrobot/hydrobot0.9.15/Scripts/Activate.ps1

#. With your venv active, install the latest version of Hydrobot using pip::

    pip install hydrobot==0.9.15

#. Record which version of dependencies you have installed in the location. The
   following cd changes the location to the relevant point, and the pip freeze
   records which dependencies are installed by the hydrobot install process for
   if auditing/reprocessing is required later::

    cd C:/Hydrobot/hydrobot0.9.15/
    pip freeze > dependencies.txt

Processing Steps
---------------------------------------
There are 3 main steps for using Hydrobot:

#. Generate the scripts

#. Run the scripts

#. Copy the processed data to your desired destination

If an individual site is being processed, this simply involves creating a copy
of the protype scripts \*.py and \*.yaml for the relevant data source, running
the \*.py file, and copying data from the resulting xml.

In order to support bulk workflows when doing multiple sites, Hydrobot has the
capability to create dsns to make working with the entire processed dataset
easier. The process to bulk process data is as follows:

Generate scripts
^^^^^^^^^^^^^^^^

#. In your local git repo, navigate to \\prototypes\\tasks_copy\\

#. Find an appropriate csv or create one if none are appropriate. If the
   desired sites and data source have "depth", e.g. lake buoys, they are run
   through a separate csv to data sources without depth.

   * All csvs should have "site, from_date, to_date, data_family" as column
     titles. Site is the site name, from_date and to_date are the dates to
     process over (can be blank, in which case the archive is used to find
     the latest processed data for from_date and the current date is used
     for to_date). Optionally, additional parameters can be set via
     additional columns (for example, water temperature sets the
     "standard_measurement_name" via an optional column to deal with the
     different data sources that water temperature sites have.

   * If dealing with sites where there are multiple different measurements
     made at different altitudes (e.g. lake buoys, air temperature), the csv
     should have a column "depths" which has the different values separated
     via semicolons (;). This will create a nested folder structure with a
     batch for each measurement corresponding to each depth.


#. Open "create_hydrobot_batches.py" (or
   "create_hydrobot_batches_with_depth.py" if working with depth data sources).
   Set the parameters "site_list_path", "destination_path", and
   "dsn_destination_path".

   * site_list_path is the csv that you wish to generate sites from
   * destination_path is where your batches will go (where your site folders are)
   * dsn_destination_path is where dsn(s) will be generated (used for the final step)

#. Run the create script - this should generate the files. The base files will
   be drawn from hydrobot templates, with site name, dates, and any other
   information provided updated for that specific site.

Run the scripts
^^^^^^^^^^^^^^^

#. Make sure your virtual environment is set up (see initial setup
   instructions) and activate it. To activate, in your shell type the location
   of the "Activate.ps1" script in the venv/Scripts folder, e.g.::

    C:/Hydrobot/hydrobot0.9.15/Scripts/Activate.ps1

   You can ensure it is active by typing `gcm python` and confirm that your
   python interpreter (under "Source") is running from your venv folder. You
   should also see a (venv) at the start of the command line.

#. To run many scripts, find the .bat file generated in "dsn_destination_path".
   Run this bat file from your shell (or copy the text into the shell). This
   opens many hydrobot scripts in parallel instances (allowing for faster
   processing).

#. To run a single script, run the desired python script in the site folder, e.g.::

    python hydrobot_run.py

#. If all goes well, the processing script will generated "merged.html" showing
   a diagnostic dash for your site. Use this to identify any issues in the
   site. If any issues are identified, the script/yaml can be modified as
   appropriate and the script rerun.

Copy processed data
^^^^^^^^^^^^^^^^^^^

#. Use Hilltop to open the dsn generated in the first step. Copy all the data
   into a temporary empty hts. Ensure all the data you expect is in the hts.
   (Note - the dsn will show most data, but can have some issues displaying,
   especially with check data).

#. When happy the data is copyed correctly, copy from the dsn to the desired
   archive (e.g. ED provisional automation).

#. In your local git repo, open the \prototypes\dsn_copy\add_dsn_audit_trial.py
   script.

#. At the bottom of the script, you should see a "if __name__==__main__"
   section which runs the function "write_to_access_for_dsn". Set "source_dsn"
   to the path to the dsn (make sure to use an r"" string to avoid escape
   character), and destination to the path to the archive (again using r
   strings). Run the file. This file ensures that the audit trail is preserved.


Credits
========

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template. Furthermore,
Sam is a real champ with the coding and whatnot. Thanks Sam.

Aww thanks Nic. You also da man <3

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
