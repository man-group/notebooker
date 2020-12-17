# Dev environment setup

Dev environment setup is largely the same as setup in the tutorial, but instead of pip installing the version
in pypi, you can set up using `python setup.py develop`.


# Contributing
In pull requests please:
* cite the issue reference 
* update the changelog (create a new version if there is no release candidate)

Please make sure that you have
run [Black](https://black.readthedocs.io/en/stable/), [mypy](http://mypy-lang.org/), 
and [flake8](https://flake8.pycqa.org/en/latest/) before you submit your changes. 
The build will fail for flake8 and Black changes.
PRs without a test will almost certainly be rejected. 
Do also make sure to run the webapp and make sure you haven't broken anything.

# Releasing a new version
When releasing a new version, please increment the version number in:
* `notebooker/_version.py`
* `.circleci/config.yml`
* `docs/config.yml`
* `notebooker/web/static/package.json`

This build will validate that these numbers match those given in `.circleci/config.yml`.

