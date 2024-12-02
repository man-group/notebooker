import git
import pytest

DUMMY_REPORT_PY = """
# ---
# jupyter:
#   celltoolbar: Tags
#   jupytext_format_version: '1.2'
#   kernelspec:
#     display_name: spark273
#     language: python
#     name: spark273
# ---

# %matplotlib inline
import pandas as pd
import numpy as np
import random

# + {"tags": ["parameters"]}
n_points = random.choice(range(50, 1000))
# -

idx = pd.date_range('1/1/2000', periods=n_points)
df = pd.DataFrame(np.random.randn(n_points, 4), index=idx, columns=list('ABCD'))
df.plot()

cumulative = df.cumsum()
cumulative.plot()
"""

DUMMY_FAILING_REPORT = """
# ---
# jupyter:
#   celltoolbar: Tags
#   jupytext_format_version: '1.2'
#   kernelspec:
#     display_name: spark273
#     language: python
#     name: spark273
# ---


# + {"tags": ["parameters"]}
n_points = 1
# -

1/0
"""

DUMMY_REPORT_IPYNB = """
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "%matplotlib inline",
    "import pandas as pd",
    "import numpy as np",
    "import random"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "tags": [
     "parameters"
    ]
   },
   "outputs": [],
   "source": [
    "n_points = random.choice(range(50, 1000))"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "idx = pd.date_range('1/1/2000', periods=n_points)",
    "df = pd.DataFrame(np.random.randn(n_points, 4), index=idx, columns=list('ABCD'))",
    "df.plot()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "lines_to_next_cell": 2
   },
   "outputs": [],
   "source": [
    "cumulative = df.cumsum()",
    "cumulative.plot()"
   ]
  }
 ],
 "metadata": {
  "celltoolbar": "Tags",
  "jupytext": {
   "cell_metadata_json": true,
   "notebook_metadata_filter": "celltoolbar,jupytext_format_version"
  },
  "kernelspec": {
   "display_name": "spark273",
   "language": "python",
   "name": "spark273"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""


@pytest.fixture
def setup_workspace(workspace):
    (workspace.workspace / "templates").mkdir()
    git.Git(workspace.workspace).init()
    (workspace.workspace / "templates/fake").mkdir()

    py_report_to_run = workspace.workspace / "templates/fake/py_report.py"
    py_report_to_run.write_text(DUMMY_REPORT_PY)

    ipynb_report_to_run = workspace.workspace / "templates/fake/ipynb_report.ipynb"
    ipynb_report_to_run.write_text(DUMMY_REPORT_IPYNB)

    report_to_run_failing = workspace.workspace / "templates/fake/report_failing.py"
    report_to_run_failing.write_text(DUMMY_FAILING_REPORT)
