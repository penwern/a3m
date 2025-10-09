Settings
========

Users can provide service settings via the ``/etc/a3m/a3m.conf`` configuration
file, e.g.::

    [a3m]
    debug = False

Environment strings are also supported and they are evaluated last, e.g.::

    env A3M_DEBUG=yes a3m ...

Configuration settings are not properly described yet, but here's the list:

Database Configuration
----------------------

a3m supports both SQLite (default) and PostgreSQL as database backends.

**SQLite** (Default)

SQLite is used by default for single-user deployments. It limits ``concurrent_packages`` to 1 due to write contention limitations::

    [a3m]
    db_engine = django.db.backends.sqlite3
    db_name = /path/to/db.sqlite

**PostgreSQL** (Recommended for Concurrent Processing)

PostgreSQL enables true concurrent package processing, allowing multiple packages to be processed simultaneously. To use PostgreSQL::

    [a3m]
    db_engine = django.db.backends.postgresql
    db_name = a3m_database
    db_user = a3m_user
    db_password = your_secure_password
    db_host = localhost
    db_port = 5432

Or via environment variables::

    export A3M_DB_ENGINE=django.db.backends.postgresql
    export A3M_DB_NAME=a3m_database
    export A3M_DB_USER=a3m_user
    export A3M_DB_PASSWORD=your_secure_password
    export A3M_DB_HOST=localhost
    export A3M_DB_PORT=5432

With PostgreSQL, the system will automatically enable concurrent package processing based on CPU count (defaults to half of available CPUs). This significantly improves throughput for batch processing scenarios.

Configuration Settings
----------------------

* ``debug`` (boolean)
* ``batch_size`` (int)
* ``concurrent_packages`` (int)
* ``rpc_threads`` (int)
* ``worker_threads`` (int)
* ``shared_directory`` (string)
* ``temp_directory`` (string)
* ``processing_directory`` (string)
* ``rejected_directory`` (string)
* ``capture_client_script_output`` (boolean)
* ``removable_files`` (string)
* ``secret_key`` (string)
* ``prometheus_bind_address`` (string)
* ``prometheus_bind_port`` (string)
* ``time_zone`` (string)
* ``db_engine`` (string) - Database backend engine. Default: ``django.db.backends.sqlite3``. For PostgreSQL use: ``django.db.backends.postgresql``
* ``db_name`` (string) - Database name or path (for SQLite)
* ``db_user`` (string) - Database user (not used for SQLite)
* ``db_password`` (string) - Database password (not used for SQLite)
* ``db_host`` (string) - Database host (not used for SQLite)
* ``db_port`` (string) - Database port (not used for SQLite)
* ``rpc_bind_address`` (string)
* ``s3_enabled`` (boolean)
* ``s3_endpoint_url`` (string)
* ``s3_region_name`` (string)
* ``s3_access_key_id`` (string)
* ``s3_secret_access_key`` (string)
* ``s3_use_ssl`` (boolean)
* ``s3_addressing_style`` (string)
* ``s3_signature_version`` (string)
* ``s3_bucket`` (string)
* ``org_id`` (string)
* ``org_name`` (string)

For greater flexibility, it is also possible to alter the applicatin settings
module manually. This is how our :mod:`a3m.settings.common` module looks like:

.. literalinclude:: ../a3m/settings/common.py
