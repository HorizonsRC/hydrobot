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
  * Identifying and removing 'flatlining' data, where an instrument repeats it's last collected data point
  * Identifying gaps and gap lengths and closing small gaps
  * Quality coding data based on NEMS standards

* Plotting data, including:

  * Processed data with quality codes
  * Comparing raw data to processed data
  * Plotting data near checks
  * Plotting data near gaps

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
