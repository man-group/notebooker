# Dev environment setup

Dev environment setup is largely the same as setup in the tutorial, but instead of pip installing the version
in pypi, you can set up using `python setup.py develop`.


# Contributing
In pull requests please cite the issue reference and update the changelog. Please make sure that you have
run [Black](https://black.readthedocs.io/en/stable/), [mypy](http://mypy-lang.org/), 
and [flake8](https://flake8.pycqa.org/en/latest/) before you submit your changes. Do also make sure to run the 
webapp and make sure you haven't broken anything.

When releasing a new version, increment the version number in `notebooker/_version.py`.

