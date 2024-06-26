============
Contributing
============

Dependency management
---------------------

Python dependencies
^^^^^^^^^^^^^^^^^^^

The requirements are listed in ``/pyproject.toml``. The constraints are relaxed
with the purpose of allowing a3m to be used as a library.

We use `uv` which pins the requirements in ``requirements.txt`` and
``requirements-dev.txt`` for our Docker image. We provide a few helpers:

* ``make pip-compile`` generates the requirements with the latest versions of
  dependencies that satisfy the constraints in ``pyproject.toml``, but does not
  update versions if they are already satisfied.
* ``make pip-upgrade`` regenerates the requirements, forcibly upgrading all
  listed packages to their latest available versions within the constraints.
* ``make pip-sync`` installs the requirements in your current environment.

Our routine to keep up with the dependencies::

    make pip-upgrade
    make pip-sync
    git add requirements.txt requirements-dev.txt
    git commit -m "Update dependencies"

At this point you can also look up new versions beyond our constraints, e.g.::

    $ pip list --outdated
    Package Version Latest Type
    ------- ------- ------ -----
    Django  4.2.9   5.0.1  wheel
    lxml    4.9.4   5.1.0  wheel
    urllib3 2.0.7   2.1.0  wheel

Update the constraints in ``pyproject.toml`` as needed, use ``pip-compile`` to
generate the requirements and ``pip-sync`` to update your environment. As you're
adopting new major versions of the dependencies, please make sure that you
understand how that impacts our project.

pre-commit
^^^^^^^^^^

pre-commit is a framework we use for managing and maintaining pre-commit hooks.
The easiest way to discover and apply new updates is to run::

    pre-commit autoupdate

Commit the changes and run pre-commit again with::

    tox -e pre-commit

Python version
^^^^^^^^^^^^^^

There is a pinned version of Python in ``/.python-version`` that we use when
packaging our Docker image and other development-oriented tools. The preference
is to use the latest version available. Currently:

.. include:: ../.python-version
   :code:

But we aim to support at least a couple of versions, e.g. 3.11 and 3.12 to
provide greater flexibility since a3m is also distributed as a Python package
serving both as an application and a library. We're using tox to test against
multiple versions of Python. If you want to alter the list of versions we're
testing and supporting, the following files must be considered:

* ``pyproject.toml`` describes the minimum version supported
  (``requires-python``), a list of all versions supported (``classifiers``) and
  test environments (under ``[tool.tox]``)
* ``.github/workflows/test.yml`` lists the testing matrix in CI.

Releases
--------

We aim to further enhance and automate our release process.

Please adhere to the following instructions:

1. Update the ``main`` branch with the latest version (``a3m.__version__``) and
   the changelog (use ``scriv collect`` to populate ``CHANGELOG.rst``). Submit
   these changes through a pull request and merge it once all checks have
   passed.
2. Confirm that the checks are also passing in ``main``.
3. Create and push the git tag, e.g.::

    $ git tag v0.7.7
    $ git push origin refs/tags/v0.7.7

   This should have triggered the publishing workflow. Please confirm that the
   new version of the package is available on `PyPI`_ and that the container
   image has been published to the `GitHub Container Registry`_.


.. _PyPI: https://pypi.org/project/a3m/
.. _GitHub Container Registry: https://ghcr.io/artefactual-labs/a3m
