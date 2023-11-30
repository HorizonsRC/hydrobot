.. highlight:: shell

============
Installation
============


Stable release
--------------

To install Hydrobot, run this command in your terminal:

.. code-block:: console

    $ pip install hydrobot

This is the preferred method to install Hydrobot, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for Hydrobot can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/nicmostert/hydrobot

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/nicmostert/hydrobot/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/nicmostert/hydrobot
.. _tarball: https://github.com/nicmostert/hydrobot/tarball/master


Usage
-----

For purposes of auditing data changes, you may want to track what changes to
the data are made, and what version of hydrobot (and it's dependencies) are
used.

    Windows

In Powershell:

.. code-block:: console

    cd path/to/Hydrobot_install
    python -m venv /path/to/Hydrobot_install/venv
    path/to/Hydrobot_install/venv/Scripts/Activate.ps1
    pip install hydrobot
    pip freeze > requirements.txt
