=======
History
=======

0.1.0 (2023-09-27)
------------------

* First release on PyPI.

0.2.0 (2023-09-27)
------------------

* Hydrobot now annals the "Processor" class, which has capabilities to process data within the single object. Class_script gives an example of this method of processing.

0.2.1 (2023-09-27)
------------------

* Including the config files, + getting wheeled boi

0.2.2 (2023-09-27)
------------------

* Ok, actually including the config files (promise, but my fingers are crossed behind my back)

0.2.3 (2023-11-30)
------------------

* Fixed some tests and hopefully fixed the config file issue this time.

0.3.0 (2023-12-11)
------------------

* Can delete data now.

0.3.1 (2023-12-12)
------------------

* No longer exports the ending QC0 data.
* Changed to pyproject.toml to get with the times.

0.3.2 (2023-12-12)
------------------

* Fixed a documentation build bug

0.3.3 (2023-12-12)
------------------

* Fixed a documentation build bug again.

0.3.4 (2023-12-12)
------------------

* Implementing the QC0 data removal tool promised in 0.3.1

0.4.0 (2024-01-30)
------------------

* XML backend and exporting support added.

0.5.0 (2024-04-03) - Alpha Release
----------------------------------

* Plotly diagnostics added.
* Support for external (to Hilltop) check data added.
* Hybrid workflow supported and documented.

0.5.1 (2024-04-03)
----------------------------------

* Updated documentation for workflow
* Added a supplementary R script to repo

0.5.2 (2024-04-10)
----------------------------------

* Updated from standard plotly to streamlit dash
* Added to QC encoder: Water Temp downgraded to 200 if last check longer than 2 months ago.

0.6.0 (2024-05-13)
----------------------------------

* Processor object now works with pd.Dataframes rather than pd.Series
* Out of validation range now has adjustable ranges, can support multiple maximum QCs with different time period lengths
* Changes to data and quality codes now have reason codes associated with any changes
* Check data can be read from xml directly
* Any missing xml data is no longer read in as zeroes
* Added in a constant shift value in config.yaml
* Various DevOps improvements

0.6.1 (2024-05-16)
----------------------------------

* DO semi-supported, but things are a little hairy rn
* Gonna officially support DO next minor release with more testing
* DO evaluator supported
* 100% 500 qc cap supported
* Support WT + AP QCs
* AP VM adjustment supported
* Nic promises the check data hilltop import thing is fixed this time
