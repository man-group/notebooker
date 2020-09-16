Welcome to Notebooker's documentation!
======================================

Introduction
------------

Jupyter Notebooks are a great way to sketch out research ideas in an interactive
environment. With cached computations and out-of-order execution allowing for instant feedback,
they are a powerful tool for researchers and technologists alike. However, when it comes to taking these
ideas and insights from Jupyter, there can be a lot of headache
to quickly transform the code from Jupyter into something which gives you a reproducible and parametrisable
report.

For example, if you wanted to execute a Notebook for $MSFT, $AAPL, and $FB which analyses price movement
over the last N days, normally you would have to either produce multiple Notebooks and export them through
awesome services like Voilà or nbviewer. But what if we can get away with only writing one notebook once?

With Notebooker, you can add parameters to a Jupyter Notebook: in this case we would
add a "stock" parameter and an "N" parameter.
Converting this into a Notebook Template and executing this through Notebooker means that your Jupyter Notebook is:

* **reviewable** - is converted from .ipynb to .py
* **templated** - is a template for 10s or 100s of reports with the same or similar output requirements
* **stored as code** - is stored in a git repository in a simple, readable format
* **testable** - can be regression tested out-of-the-box
* **executable** - is executable from command line or the Notebooker webapp
* **browsable** - has results viewable from webapp or emailed to you
* **historical** - all previous results for a template are easily accessible through the webapp
* **secured** - optional support for OAuth-provided endpoints to prevent unauthorised webapp access

Notebooker allows you to execute Jupyter Notebooks with parameters either via
a webapp front-end or a CLI. The notebooks are converted into "notebook templates" which, when executed by Notebooker,
transform the interactive notebooks into static parametrised reports: all with a
handy front-end for execution and viewing of results.

With only a few clicks, you can go from Jupyter Notebook to having a reproducible
report displayed on a webapp.



.. automodule:: notebooker
   :members:

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   setup
   templates
   report_execution
   webapp/webapp
   webapp/urls


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
