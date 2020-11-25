.. _Notebook Templates:

Intro to Notebook Templates
==================================

Creating a Notebook Template
----------------------------
To create a Notebook Template, we use a tool called :code:`jupytext`.
It allows for interchangeably converting between :code:`.ipynb` and :code:`.py` files.
To create your own template from an existing :code:`.ipynb` file, you can either
follow the instructions for installation `on their homepage <https://github.com/mwouts/jupytext>`_, or
use :code:`convert_ipynb_to_py` directly from the console when Notebooker is installed.

The purpose of a notebook template is to allow you to write Jupyter notebooks as normal, and then
commit them into source control as python files: allowing for simple diffs and control
over how notebooks are promoted into the live Notebooker environment for execution.

Where should templates go?
--------------------------
It is possible (and encouraged) to use a separate git repository version controlling notebook templates.
To use a git repository as a notebook templates repository, you simply need to create a folder called
:code:`notebook_templates/` which contains the .py template files. Additionally, a
:code:`notebook_requirements.txt`, containing extra package requirements to be
installed, should be added to that folder.

For Notebooker to use a your checked-out repository, set two environment variables:

* Set :code:`PY_TEMPLATE_BASE_DIR` to the checked-out repository
* Set :code:`PY_TEMPLATE_SUBDIR` to the subdirectory within your git repo which contains the templates

Adding parameters
-----------------
By adding parameters to your jupyter notebooks, Notebooker allows you to turn your notebooks
from static reports into dynamically-generated templates. For example, if you want to run a notebook
for every G10 currency, it is possible to write one report and run it with 10 different parameters.

To add a parameter, create a cell with the tag "parameters" which contains all of the static parameters which
you'd like to be able to parametrize. It's that simple! For more information, see the readme within
`papermill's documentation <https://papermill.readthedocs.io/en/latest/usage-parameterize.html>`_.

Testing Notebook Templates
--------------------------
If you'd like, it's possible to set up tests for your notebook templates using a 3rd party CI tool
such as Jenkins. Two tools are provided as command line entrypoints for template testing and verification:

* :code:`notebooker_template_sanity_test` - A quick test to ensure that the notebook templates are formatted correctly.
* :code:`notebooker_template_regression_test` - A longer test to ensure that the notebook templates can all be executed with their default parameters.
