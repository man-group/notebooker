The Notebooker webapp
=====================

Notebooker's primary interface is a simple webapp written to allow users to view and
run Notebooker reports. It first displays all unique template names which have ever run, and a drill-down
view lists all results for that notebook template in a handy grid, allowing for rerunning
and parameter tweaking.
The entrypoint used to run Notebooks via the webapp is the
same as the external API; as long as you are using the same environment (e.g. within
a docker image) you will get consistent results.


Report dashboard
----------------
The home page of the Notebooker webapp displays an overview of all reports which have recently run.

.. image:: /images/nbkr_homepage.png
   :width: 400
   :alt: Screenshot of Notebooker webapp homepage

Clicking on one of these elements will bring up an overview of all reports which have recently run.
It is possible to view each full report by clicking "Result". It's also possible to rerun, delete, and
copy parameters of each report in the grid.

.. image:: /images/nbkr_results_listing.png
   :width: 400
   :alt: Screenshot of Notebooker results listing


Running a report
----------------
| First, you should click "Execute a Notebook" which is at the top of every page within the Notebooker webapp.
  This brings up a sidebar which shows the available results. Click on one to go to the "run report" interface.

.. image:: /images/sidebar.png
   :width: 400
   :alt: Screenshot of Notebooker webapp sidebar

| On the "Run a report" interface, you can see "Customise your report" on the
  left side and a preview of your notebook on the right. Here you can see where the parameters cell is,
  and therefore what can be overridden in the "Override parameters" box, highlighted in yellow.

.. image:: /images/nbkr_run_report.png
   :width: 400
   :alt: Screenshot of Notebooker "Run Report" interface

.. warning::
    In order to prevent users having to write JSON, the Override parameters box actually takes raw python statements
    and converts them into JSON. Therefore, it is strongly recommended that you run Notebooker in an environment
    where you either completely trust all of the user base, or within a docker container
    where executing variable assignments will not have any negative side-effects.

Customisable elements:

* Report Title - the name of the report which will appear on the main screen and email subject upon completion. Can be left blank.
* Override parameters - the values which will override the parameters in the report (in python). Can be left blank.
* Email to - upon completion of the report, who should it be emailed to? Can be left blank.
* Generate PDF output - whether to generate PDFs or not. Requires xelatex to be installed - see :ref:`export to pdf`
* Hide code from email and PDF output - whether to display the notebook code when producing output emails and PDFs.

Viewing results
---------------
| Once you have started running a report, a progress screen will show you the current status of the report
  including its status, a live-updating log of stdout/stderr, and additional metadata in the sidebar.

.. image:: /images/nbkr_running_report.png
   :width: 400
   :alt: Screenshot of Notebooker "Running Report" interface

If the job fails, the stack trace will be presented to allow for easier debugging.

.. image:: /images/error.png
   :width: 400
   :alt: Screenshot of an error


| If the job succeeds, the .ipynb will have been converted into HTML for viewing on this page.
| **Please note** for user convenience, all notebook code is hidden by default.
| You can also get to this view by clicking the blue "Result" button on the homepage.
| If you are using a framework such as seaborn or matplotlib, the images will be available and served by the webapp.
| If you are using plotly, you can use offline mode to store the required javascript within the HTML render,
  or using online mode (recommended) so that the serialised notebook results are not too large.

.. image:: /images/nbkr_results.png
   :width: 400
   :alt: Screenshot of a successful report

It is also possible to either rerun a report from this view, or to clone its parameters. If it was saved as a PDF,
you can download using the button on the sidebar, or you can download as raw .ipynb. You can view and copy
the stdout from the run via a modal by clicking the "View Stdout" button on this view.


Scheduling a report
-------------------
Once you are happy with your report, you can choose to schedule the report within the Notebooker webapp.
Setting up a schedule is relatively simple, and it begins in the Scheduler tab.

.. warning::
    In order for a schedule to be executed successfully, the Notebooker webapp must be running. Upon restart,
    the latest schedule is *not* executed and instead the scheduler will wait until the next scheduled slot.

First, click the "Add a Schedule" button:


.. image:: /images/add_a_schedule_button.png
   :width: 600
   :alt: Screenshot of the Add a Schedule button

Then fill out the form. Please note that the schedule is in Cron syntax - please see
`the APScheduler docs <https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html>`_ for more
information.


.. image:: /images/new_schedule.png
   :width: 600
   :alt: Screenshot of the new scheduler form.


Once the schedule has been saved, it will appear in the list under the scheduler tab.
If you wish to modify a schedule, you can click on the row and it will pop up the same modal. Please note
that the report name cannot be changed. Reports can also be deleted from this table by clicking on the trash icon.

.. image:: /images/existing_schedules.png
   :width: 600
   :alt: Screenshot of the scheduler tab.


Once the schedule has been triggered and the job has run, a new entry will appear on the homepage and the results
will be accessible. You can tell it has been scheduled by the presence of a Scheduler button.

.. image:: /images/finished_schedule_jobs.png
   :width: 600
   :alt: Screenshot of the homepage with completed, scheduled jobs.


Rerunning a report
------------------
There are three ways to rerun a report in the Notebooker webapp.

1. "Rerun" from the homepage
2. "Rerun" from the result page
3. "Clone parameters" from the result page

The first two options work the same - you rerun the report with exactly the same parameters again.
All reruns have the title "Rerun of <prior report title>".
The latter option, clone parameters, takes you to the "run a report" screen but with the parameters from that
report copied into the "override parameters" box.


Configuring the webapp
----------------------
The webapp itself is configured via the command line notebooker-cli:

.. click:: notebooker._entrypoints:base_notebooker
   :prog: notebooker-cli
   :nested: full


Read-only mode
--------------
There exists a read-only mode (add :code:`--readonly-mode` to command line arguments) in the
Notebooker webapp which will disable the ability to run new,
rerun, or delete existing reports. This mode is useful in situations where you would like Notebooker
reports to be executed by a trusted process (e.g. the internal scheduler, or an external job scheduling engine)
but you don't want users to be able to directly execute Notebooks. This is suited well to production
environments or where the reports can reveal sensitive data if misconfigured.

.. image:: /images/finished_schedule_jobs.png
   :width: 600
   :alt: Screenshot of the homepage with completed, scheduled jobs.

.. note::
    Please note that read-only mode does not change the functionality of the scheduler; users will still be able to
    modify schedules and it will execute as intended. To disable the scheduler you can add :code:`--disable-scheduler`
    to the command line arguments of the webapp; likewise git pulls can be prevented by using :code:`--disable-git`.
