0.2.1 (????-??-??) 
------------------
No changes (yet!)


0.2.0 (2020-12-17)
------------------
* Code output can now be hidden from PDF and email output! Either check the box in the "Run Report" dialog or, using the cli, use the new `--hide-code` option.
* Performance improvement for queries


0.1.0 (2020-11-30)
------------------
Support for database plugins and tidying up configuration to be consistent across the board.

**Breaking changes**
* 3 primary entrypoints have been consolidated under one - notebooker-cli, e.g. `notebooker-cli start-webapp` and `notebooker-cli execute-notebook`. Run notebooker-cli --help for more info. 
* In config, PY_TEMPLATE_DIR has been renamed to PY_TEMPLATE_BASE_DIR
* In config, GIT_REPO_TEMPLATE_DIR has been renamed to PY_TEMPLATE_SUBDIR

0.0.2 (2020-10-25)
------------------
Bugfixes & cleanup
Docker support (#14)


0.0.1 (2020-09-04)
------------------
Initial release of Notebooker
