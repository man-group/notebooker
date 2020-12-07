Report Execution
================

How does it work?
-----------------
Reports are generated when we execute a Notebook Template. They follow this simple workflow:

1. Find the Notebook Template .py file on disk.
2. Convert the Notebook Template to .ipynb using Jupytext.
3. Execute the Notebook using Papermill using parameters, if provided. (NB: This executes using the `notebooker_kernel` kernel)
4. The result is converted to .html using `nbconvert`
5. (Optional) The result is converted to PDF
6. (Optional) Results are sent to the provided email address(es)
7. Results are saved into mongo with `status=NotebookResultComplete`


Executing a Notebook
--------------------
There are two primary ways to do this: either through the webapp or through the entrypoint. Both
of these methods will rely on a `notebooker_kernel` being available in the current ipykernel environment.

For more information on the entrypoint, please run: `notebooker-cli execute-notebook --help`

Technologies
------------
Notebooker leverages multiple open-source technologies but in particular, it heavily makes use of some
awesome projects which deserve special attention:

* `Jupytext <https://github.com/mwouts/jupytext>`_
* `papermill <https://github.com/nteract/papermill>`_
* `nbconvert <https://github.com/jupyter/nbconvert>`_
* `flask <https://github.com/pallets/flask>`_
