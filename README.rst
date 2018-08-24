GS: A minimalistic Google Storage client
========================================

*gs* is a command line interface (CLI) that provides a set of essential commands for
`Google Cloud Storage <https://cloud.google.com/storage/>`_. It is modeled after the AWS CLI's ``aws s3`` command. Its
features are:

* Python 3 compatibility
* A minimalistic set of dependencies
* A tiny footprint

Installation
~~~~~~~~~~~~
::

   pip install gs

Synopsis
~~~~~~~~
Usage:
  ``gs [OPTIONS] COMMAND [ARGS]...``

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
   +------------------+--------------------------------------------------+
   | ``gs configure`` | Set gs config options, including the API key.    |
   +------------------+--------------------------------------------------+
   | ``gs cp``        | Copy files to, from, or between buckets.         |
   +------------------+--------------------------------------------------+
   | ``gs ls``        | List buckets or objects in a bucket/prefix.      |
   +------------------+--------------------------------------------------+
   | ``gs mb``        | Create a new bucket.                             |
   +------------------+--------------------------------------------------+
   | ``gs mv``        | Move files to, from, or between buckets.         |
   +------------------+--------------------------------------------------+
   | ``gs rb``        | Permanently delete an empty bucket.              |
   +------------------+--------------------------------------------------+
   | ``gs rm``        | Delete objects (files) from buckets.             |
   +------------------+--------------------------------------------------+
   | ``gs sync``      | Sync a directory of files with bucket/prefix.    |
   +------------------+--------------------------------------------------+

Run ``gs configure`` to configure Google service account access credentials that will be used by the
``gs`` command. You can create a new service account key at https://console.cloud.google.com/iam-admin/serviceaccounts.

Credentials
~~~~~~~~~~~
Before making API calls, *gs* ingests API credentials in the following order of priority:

- First, *gs* checks if a ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable is set. If so, it attempts to load and use
  credentials from the service account credentials filename referenced by the variable.
- If that varible is not set, *gs* attempts to load service account credentials previously configured with ``gs configure``
  (stored in ``~/.config/gs/config.json``).
- If that fails, *gs* attempts to load a service account API token from
  `Google instance metadata <https://cloud.google.com/compute/docs/storing-retrieving-metadata>`_.
- If that fails, *gs* gives up and prints an error.

.. image:: https://travis-ci.org/kislyuk/gs.png
   :target: https://travis-ci.org/kislyuk/gs
.. image:: https://img.shields.io/pypi/v/gs.svg
   :target: https://pypi.python.org/pypi/gs
.. image:: https://img.shields.io/pypi/l/gs.svg
   :target: https://pypi.python.org/pypi/gs
.. image:: https://codecov.io/gh/kislyuk/gs/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/kislyuk/gs
