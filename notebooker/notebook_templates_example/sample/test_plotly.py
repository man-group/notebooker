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
import numpy as np
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

init_notebook_mode(connected=False)

# + {"tags": ["parameters"]}
x_n = 2000
y_n = 2070
# -

x = np.random.randn(x_n)
y = np.random.randn(y_n)

import plotly.graph_objs as go

iplot(
    [
        go.Histogram2dContour(x=x, y=y, contours=dict(coloring="heatmap")),
        go.Scatter(x=x, y=y, mode="markers", marker=dict(color="white", size=3, opacity=0.3)),
    ],
    show_link=False,
    image_width=100,
)
