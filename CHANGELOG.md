0.1.0 (2020-11-30)
------------------
Support for database plugins and tidying up configuration to be consistent across the board.

**Breaking changes**
* 3 primary entrypoints have been consolidated under one - notebooker_cli, e.g. `notebooker_cli start-webapp` and `notebooker_cli execute-notebook`. Run notebooker_cli --help for more info. 
* In config, PY_TEMPLATE_DIR has been renamed to PY_TEMPLATE_BASE_DIR
* In config, GIT_REPO_TEMPLATE_DIR has been renamed to PY_TEMPLATE_SUBDIR

0.0.2 (2020-10-25)
------------------
Bugfixes & cleanup
Docker support (#14)


0.0.1 (2020-09-04)
------------------
Initial release of Notebooker
