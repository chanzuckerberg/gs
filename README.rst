GS: A minimalistic Google Storage client
========================================

*gs* is a command line interface (CLI) and Python library that provides a set of essential commands for
`Google Cloud Storage <https://cloud.google.com/storage/>`_. It is modeled after the AWS CLI's ``aws s3`` command. Its
features are:

* Python 3 compatibility
* A minimalistic set of dependencies
* A tiny footprint
* Intuitive convention-driven configuration of API credentials without browser login prompts
* Checksum validation to ensure end-to-end data integrity in uploads and downloads
* Progress bars for long-running upload and download operations
* Resumable uploads and downloads
* Multithreaded directory sync and batch delete, capable of handling large numbers of objects
* An attractive paging and table layout interface
* A JSON object metadata output mode for feeding data to other utilities

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
   | ``gs ls``        | List buckets or objects in a bucket/prefix.      |
   +------------------+--------------------------------------------------+
   | ``gs cp``        | Copy files to, from, or between buckets.         |
   +------------------+--------------------------------------------------+
   | ``gs mv``        | Move files to, from, or between buckets.         |
   +------------------+--------------------------------------------------+
   | ``gs mb``        | Create a new Google Storage bucket.              |
   +------------------+--------------------------------------------------+
   | ``gs rb``        | Permanently delete an empty bucket.              |
   +------------------+--------------------------------------------------+
   | ``gs rm``        | Delete objects (files) from buckets.             |
   +------------------+--------------------------------------------------+
   | ``gs sync``      | Sync a directory of files with bucket/prefix.    |
   +------------------+--------------------------------------------------+
   | ``gs api``       | Use httpie to perform a raw HTTP API request.    |
   +------------------+--------------------------------------------------+
   | ``gs presign``   | Get a pre-signed URL for accessing an object.    |
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

Using the Python library interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from gs import GSClient
    client = GSClient()
    object_meta = client.get("b/my-bucket/o/my-object")
    with client.get("b/my-bucket/o/my-object", params=dict(alt="media"), stream=True) as res:
        object_bytes = res.raw.read()
    presigned_url = client.get_presigned_url("my-bucket", "my-object", expires_at=time.time()+3600)

Authors
-------
* Andrey Kislyuk

Links
-----
* `Project home page (GitHub) <https://github.com/chanzuckerberg/gs>`_
* `Package distribution (PyPI) <https://pypi.python.org/pypi/gs>`_
* `Change log <https://github.com/chanzuckerberg/gs/blob/master/Changes.rst>`_
* `GCB builds <https://console.cloud.google.com/cloud-build/builds>`_
* `Google Cloud Storage <https://cloud.google.com/storage/>`_

Bugs
~~~~
Please report bugs, issues, feature requests, etc. on `GitHub <https://github.com/chanzuckerberg/gs/issues>`_.

License
-------
Licensed under the terms of the MIT License.

.. image:: https://travis-ci.com/chanzuckerberg/gs.png
   :target: https://travis-ci.com/chanzuckerberg/gs
.. image:: https://img.shields.io/pypi/v/gs.svg
   :target: https://pypi.python.org/pypi/gs
.. image:: https://img.shields.io/pypi/l/gs.svg
   :target: https://pypi.python.org/pypi/gs
.. image:: https://codecov.io/gh/chanzuckerberg/gs/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/chanzuckerberg/gs
