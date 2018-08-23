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

Run ``gs configure`` to configure Google service account access credentials that will be used by the
``gs`` command. You can create a new service account key at https://console.cloud.google.com/iam-admin/serviceaccounts.

.. image:: https://travis-ci.org/kislyuk/gs.png
   :target: https://travis-ci.org/kislyuk/gs
.. image:: https://img.shields.io/pypi/v/gs.svg
   :target: https://pypi.python.org/pypi/gs
.. image:: https://img.shields.io/pypi/l/gs.svg
   :target: https://pypi.python.org/pypi/gs
.. image:: https://codecov.io/gh/kislyuk/gs/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/kislyuk/gs
