# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .md
#       format_name: markdown
#       format_version: '1.1'
#       jupytext_version: 1.1.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# #Notebooker Test!


# + {"tags": ["parameters"]}
plots = 5
days = 100
start_date = "2020-01-01"

# -
# %matplotlib inline
import pandas as pd
import numpy as np

# -
arr = np.random.rand(days, plots) - 0.5
dts = np.array(start_date, dtype=np.datetime64) + np.arange(days)
df = pd.DataFrame(arr, index=dts)

# -
df.cumsum().plot()
