.. _Initial Setup:

Docker
======

The docker-compose setup in the docker directory will bring up a demo instance which is exposed
on your port 8080 of your local machine. It can be used as a reference for your own setups.


Manual Installation
===================

Prerequisites
-------------
* python 3.6+
* `mongodb <https://www.mongodb.com/download-center/community?jmp=docs>`_ >= 2.4.x
* npm


I've only just installed mongodb
--------------------------------
Cool! First let's spin up an mongodb instance so that our notebook reports have somewhere to live.
Using mongodb also allows us to search through the metadata of completed reports, so we can do more
interesting queries

1. Start a mongo instance

.. code::

  $ mongod --dbpath <path/to/db_directory>

2. Create a mongo user

.. code::

  $ mongo
  > use admin
  > db.createUser({user: 'jon', pwd: 'hello', roles: ['readWrite']})


Install Notebooker
------------------

1. Install notebooker

.. code:: bash

    $ pip install git+https://github.com/man-group/notebooker.git


2. npm build

.. code:: bash

    pushd ./notebooker/web/static/
    npm install
    popd

3. Set up the ipykernel which runs Notebooks

.. code:: bash

    $ python -m ipykernel install --user --name=notebooker_kernel

4. Install notebook requirements

.. code:: bash

    $ pip install -r notebooker/notebook_templates_example/notebook_requirements.txt

5. Run the webapp!

.. code:: bash

    $ MONGO_HOST=localhost:27017 MONGO_USER=jon MONGO_PASSWORD=hello PORT=11828 notebooker_webapp

6. Open the link that is printed in your web browser.

.. code::

    INFO:notebooker.web.main:Notebooker is now running at http://localhost:11828`


.. _export to pdf:

Exporting to PDF
----------------

If you want to convert your output to PDF, then you will have to install xelatex, as per `nbconvert`:

.. code::

    OSError: xelatex not found on PATH, if you have not installed xelatex you may need to do so.
    Find further instructions at https://nbconvert.readthedocs.io/en/latest/install.html#installing-tex.
