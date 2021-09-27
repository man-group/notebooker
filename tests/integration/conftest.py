import git
import pytest

DUMMY_REPORT = """
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


@pytest.fixture
def setup_workspace(workspace):
    (workspace.workspace + "/templates").mkdir()
    git.Git(workspace.workspace).init()
    (workspace.workspace + "/templates/fake").mkdir()
    report_to_run = workspace.workspace + "/templates/fake/report.py"
    report_to_run.write_lines(DUMMY_REPORT.split("\n"))
