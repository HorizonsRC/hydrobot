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

0.6.2 (2024-05-20)
----------------------------------

* Fixed bug that meant that different data sources would not

0.6.3 (2024-07-01)
----------------------------------

* Fixed to_date format to YMD rather than DMY when to_date not in yaml
* Fixed water temperature R script when to_date not in yaml
* Added groundwater evaluator

0.6.4 (2024-07-25)
----------------------------------

* Added support for check-less data types such as soil moisture

0.6.5 (2024-08-09)
----------------------------------

* Made quality_encoder automatically assign qc200 for check-less data
* Fixed the missing data quality codes to fit with hilltop's funky qc system
* Added batch processing
* Yaml now specifies destination file name

0.6.6 (2024-08-27)
----------------------------------

* Adding support for infer frequency and missing record prototype

0.7.0 (2024-09-18)
----------------------------------

* Rainfall processing
* Lots of minor documentation upgrades
* Start of "processing issues", a place to store warnings for the hydrobot user

0.7.1 (2024-09-19)
----------------------------------

* Fixing installation dependencies
* Fixing ramped display

0.7.2 (2024-09-19)
----------------------------------

* Accurately representing the inaccurate recorder totals.

0.7.3 (2024-09-19)
----------------------------------

* Fixing the defusedxml dependency version

0.7.4 (2024-09-19)
----------------------------------

* Making manual tip filter more sensitive

0.7.5 (2024-09-26)
----------------------------------

* Correctly accounting for multiple site inspections
* Manual tip now deals with multiple tips in the same second

0.7.6 (2024-09-30)
----------------------------------

* Fix for Null manual tips
* Rainfall control plot now implemented correctly

0.7.7 (2024-10-17)
----------------------------------

* Fix for when the period passed to manual tip filter contains a nan
* Another edge case fix for Null manual tips (caused floats)
* Fixed quality series adding values from before start date
* Fixed rainfall script skipping values that would round up to an arrival time within the given time range
* Dipstick used when flask is not recorded, downgraded to qc400
* Updating the dashboard with additional info

0.7.8 (2024-10-31)
----------------------------------

* LTCO calculation supported
* Script cleanup for rainfall/soil moisture/air temperature

0.8.0 (2025-02-05)
----------------------------------

* Better batch processing support
* Processor can now find from_date, to_date, & frequency from the archive file
* AP, WT, and DO scripts work without R (data gathered directly from database and hilltop)
* Rainfall - Fixed manual additional points from dipstick-only inspections making later inspections qc400
* Rainfall - Added site points dictionary to issues for user verification
* Rainfall - Rainfall site survey wind now defaults to 1 point when missing (better represents the region)

0.8.1 (2025-02-13)
----------------------------------

* Various QOL improvements for rainfall
* Rainfall with no check data fixes

0.8.2 (2025-03-07)
----------------------------------

* Extreme data filter for ltco (in addition to the qc filter)
* Further rainfall with no check data fixes
* Loosened requirements for filtering manual rainfall tips, made buffer offset modifiable.

0.8.3 (2025-03-18)
----------------------------------

* Infer frequency as an option for non-constant timestep data
* DO batch processing working
* DO takes metadata from site table
* DO filters based on end of WT/AP data in prov auto
* More explicit error handling
* Calibraitons table for data sources on Sonde "fixed"
* Added capability to removing data which is marked as qc100 without being np.nan

0.8.4 (2025-03-19)
----------------------------------

* DO at depth now supported
* Trailing qc 100 quality codes are now removed in DO
* Depth profiles can be drawn from separate sites

0.9.0 (2025-06-16)
----------------------------------

* Introduced data family
* Generic initializer introduced - will find the correct processor type from yaml
* Batch processing can now be done by copying from a template
* Introduced "tasks" for copying the templates and scripts into correct files
* Various bug fixes

0.9.1 (2025-06-16)
----------------------------------
* Bug fix for package templates which prevented task copies.

0.9.2 (2025-06-17)
----------------------------------
* Rereleasing failed build
* Fixing issue where batch numbering will pick up dates etc, and where non-directory names are read

0.9.3 (2025-06-19)
----------------------------------
* Rereleasing failed build
* Updating panda to 2.3.0
* Fixing behaviour that relied on a pandas bug

0.9.4 (2025-07-01)
----------------------------------
* Correcting rounding for μL integer rainfall, related to fixed pandas 2.3.0 bug

0.9.5 (2025-07-09)
----------------------------------
* Making the import_std/chk/qual functions less state based and more functional
* They now return a single value (a dataframe)
* Removed redundant deprecated processor values like raw_standard
* Added rainfall backup ranges to template

0.9.6 (2025-10-02)
----------------------------------
* Added mass-depth runs
* Added pH/ORP/BGAlgae/Conductivity capability
* Making "tasks", to set up files for running from lists of sites/families

0.9.7 (2025-10-10)
----------------------------------
* Fixed mass batch paths
* Bug fix for new site "site surveys" with whitespace at start/end of site name
* Rainfall backup replacement now correctly caps qc to 400
* Fixed manual points shift
* Standardised naming formats
* Added measurement names to merged
* manual tip filter fix

0.9.8 (2025-11-06)
----------------------------------
* Fixed bug where multiple validations happen during one inspection
* Yaml completion now preserves formatting
* Made rainfall_site_survey read from SQL, now in source

0.9.9 (2025-12-2)
----------------------------------
* Added support for soil temperature and soil moisture processing.
