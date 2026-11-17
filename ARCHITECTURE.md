# Hydrobot architecture

How hydrobot's batch-processing architecture is meant to work, and why. Written
to be read cold. Where something is inferred rather than confirmed, it says so.

## 1. Principles

These explain most individual decisions below.

1. **Say what you need, not what you have.** Code depends on the narrowest
   interface it actually uses. The orchestrator's resolve step needs two
   provider methods, so it declares those two (`ResolveProvider`), not the whole
   `DataProvider`. Test fakes then stay tiny, and nothing depends on methods it
   never calls. The interface is defined next to its consumer.
2. **Providers report facts; callers decide what is an error.** "Never archived"
   is `None`; "no data in this range" is an empty frame. Whether that is a
   problem is the orchestrator's or processor's call.
3. **Refuse rather than guess, when a wrong guess is expensive.** Examples: no
   `from_date` for an empty archive is an error (the lookup may be misconfigured,
   and reprocessing a whole history costs far more than adding one config line);
   unsafe characters in a site name raise instead of being "cleaned";
   duplicate matching series raise instead of picking one.
4. **Hydrobot writes a file once, then it belongs to the analyst.** Setup never
   overwrites an existing config, and nothing edits it afterwards.
5. **Pure logic is separate from IO.** Expansion, resume-point, and path building
   are pure functions: dicts and tables in, dicts and tables out. Everything that
   needs a server or a disk is at the edge.
6. **Tests are documentation people can read.** Fakes with the same methods as
   the real thing; real XML fixtures run through the real parser; heavy inline
   comments explaining *why*; no cleverness that needs language trivia to follow.
   (Humans collaborate on this, not just bots.)
7. **Our dependencies are ours.** whurl and Annalist are owned by the same team.
   A bug found in them is a work item, not a constraint to design around
   (section 9).
8. **A full breaking change beats parity.** The old Processor is being replaced,
   not wrapped. Old scripts are supported only as long as strictly needed.

## 2. The three layers

| Layer | Owns | Must not |
|---|---|---|
| **Provider** | Everything source-specific: how a source names things, which files hold what, how to read data, site info, and where processing last got to. Returns hydrobot-shaped results. | Read or write YAML, know about batches, expand sites |
| **Processor** | Processing ONE run (one site, measurement, and layer), given a complete run config and a provider | Read or write config files, expand anything |
| **Orchestrator** | Batches: reads the batch config, builds the provider once, resolves entries into run configs, saves them, hands each to a processor | Know source-specific details |

Origins (live server, archive, SQL) are private to a provider. One provider call
may combine several, e.g. `get_standard` may merge a whurl call with a SQL lookup.
A provider owns its HTTP clients for its whole life: build it once, reuse it for
every read, close it once (`with HorizonsProvider(config) as provider:`). Never
wrap a single read in `with client:`: leaving that block closes the client for
good and the next read fails. (This broke the first live run.)
Providers do **not** subclass the `DataProvider` protocol (a subclass would
inherit its `...` bodies, so a forgotten method silently returns `None`).
A test checks that every protocol method exists on the class instead.

External collaborators, each to sit behind a protocol when needed:
the **Data Processing Log** (SQL status flags INITIALISED, PROCESSED/ERROR,
COMMITTED, ARCHIVED/ERROR; not yet designed), **Shadoof** (loads the XML hydrobot
writes into HTS; separate tool), **Annalist** (audit log of method calls).

## 3. Workflow and where code fits (Gen 500 scope)

Per batch (one batch number is, we infer, one data source covering many sites;
**confirm**): setup, process, review, edit, commit, archive, check archive.

- **Setup** resolves each batch entry into run configs and writes one file per
  run. This is where `resolve()` lives, so `to_date` ("now") freezes at setup.
- **Process** runs each run from its saved config. First run and reprocess are
  the same path.
- A failure in one site must not stop the batch: the orchestrator catches errors
  per run and records them (the SQL log has one row per site and data source).
- Hydrobot writes `data.xml`; Shadoof loads it into HTS (inferred from the scope
  document; **confirm**). If so, provider "export" is just serialising XML
  (whurl `to_xml()`), not writing to the source, and no write capability is needed.

Not yet built: the batch loop and error policy, the generated per-site
`script.py` and batch scripts, the `ProcessingLog` protocol, reading the batch
config file. Batch-level keys the batch config must supply: `batch`,
`measurement_folder`, `data_source_code`.

## 4. Vocabulary

- **Batch config**: what a person writes. One entry per site, maybe with
  `layers` and no dates. Read-only to hydrobot.
- **Run config**: one per site/measurement/layer, fully filled in. Created by
  `resolve()`; saved at setup; the thing the Processor takes and the unit of
  reproducibility.
- **`layers`** is a list (batch level). **`layer`** is one value (per run); a
  lone `layer` is shorthand for `layers: [x]`; giving both is an error.
  **`{layer}`** is the placeholder in templates. A layer is an opaque label, not
  necessarily a depth in mm: it may be a height or a non-ordinal name. `depth`
  is being purged in favour of `layer`; scripts for depth families say
  `data.layer / 1000.0` explicitly.
- **`layer_label`**: how a layer reads in folder and file names (e.g. `-500mm`),
  produced by the same template mechanism.

## 5. Resolve: expand, then fill

1. **Expand** (`expansion.py`, pure): `layers` plus `layer_expansion_template`
   gives one run config per layer. Templates map keys to format strings filled
   from that run's own fields, e.g. `standard_measurement_name: "pH (-{layer} mm)"`.
   Rule: templates are substitution only. Anything needing conditionals stays
   in code. This replaced the `match data_family` blocks in `data_sources.py`.
2. **Fill** (`resolve.py`, needs a provider; `now` is passed in, never read):
   - `site_code` from `provider.get_site_info(site).code` if missing.
   - `to_date` defaults to now.
   - `from_date` from `provider.last_processed_time(site, measurement)`. The
     archive lookup uses `archive_standard_measurement_name` if the run sets one,
     else the normal name. Values already present are never overwritten, and the
     provider is only asked when something is actually missing.
   - Dates are text `"%Y-%m-%d %H:%M"` (seconds dropped, i.e. restart slightly
     early, never late).
   - Empty archive plus no `from_date` is a deliberate `ValueError` naming the
     archive settings to check. A future opt-in such as `from_date: start` would
     need a new provider question ("where does this source's data begin?").

## 6. Saved run configs and folder layout

```
<root>/<measurement_folder>/<batch>/<site>[/<layer_label>]/
    <batch>_<source>_<site_code>[_<layer_label>]_<purpose>.<ext>
    e.g. Water Temperature/503/Lake Horowhenua at Buoy/-500mm/503_WT_LHB_-500mm_config.yaml
```

- `paths.py` (`run_dir`, `run_filename`) is the only code that knows this layout.
  Unsafe path characters raise. A layer folder exists only for layered runs.
  (A folder named `-500mm` starts with a hyphen, which some command-line tools
  misread; drop it from the folder name if that bites.)
- `run_configs.py`: `setup_entry` resolves one entry and writes one file per run.
  Never overwrites; all-or-nothing per entry (everything that can fail is
  checked before the first write).
- A file has a `setup:` header (hydrobot and whurl versions, `set_up_at`, source
  batch config, `filled_by_hydrobot`: every key hydrobot supplied rather than the
  user) followed by the run config. The Processor ignores the header. The header
  is never updated, even on reprocess.
- Dates, versions and `layer_label` are always double-quoted; other strings are
  quoted if plain style would be misread. `load_run_config` drops the header and
  converts a hand-edited, unquoted date back to text.
- Audit trail (what Annalist records versus this header): **deferred.** The
  header is self-contained, so nothing here blocks that decision.

## 7. Provider contracts

Each method's docstring in `protocol.py` is the contract. In short:

| Read | Found | Nothing / absent | Raises |
|---|---|---|---|
| `get_standard` | data + metadata (`item_name`, `item_format`, `divisor`, `units`, `number_format`) | empty frame, metadata only `origin` | wrong name (data returned but not this measurement); duplicates |
| `get_quality` | one column of integer codes | empty (normal: nothing processed yet) | duplicates |
| `get_check` | one column per item, typed; `metadata["items"]` in column order | empty | duplicates |
| `last_processed_time` | datetime to resume from | `None` (never archived) | archive not configured |
| `get_site_info` | `SiteInfo(code, metadata)` | n/a | not exactly one site; code field missing or blank |

- Data arrives already scaled by Hilltop divisors and typed by whurl. Callers
  must not divide or re-format. (The legacy Processor does, which is two bugs:
  values divided twice, and check items paired with columns by position, which
  mis-formats columns when `ItemInfo` is listed out of order, as real responses
  are.) Check has no fallback to a second name: the run config names it exactly.
- **The provider is the boundary for errors, too.** Callers only ever see
  `DataProviderError`, never whurl's exception types. Hilltop reports
  "nothing" as an ERROR document, in three different ways, copied from live
  responses (9 November 2026): `No data from X to Y` (a quiet range),
  `No Data Source for M at this site.` (wrong measurement), and
  `No data for site S` (wrong site). Only the first is an empty result.
  `classify_not_found` tells them apart, and the other two raise a
  `DataProviderError` that names the measurement or site, quotes the server and
  carries the request URL. Every other whurl error is also wrapped in a
  `DataProviderError` (original message kept, original exception chained).
  Unknown wording is NOT assumed to be an empty range: treating a real problem as
  "no data" hides it, while the reverse is merely loud. The exception is the
  ARCHIVE lookup (`last_processed_time`), where "not there" means "never
  archived" and all three come back as `None`. An empty range is still reported
  by the caller, with its `request_url`.
- **Origin.** Every data read records `metadata["origin"]` (provider,
  `source_tag` such as `HTP`, `base_url`, `hts`, `request_url`, site,
  measurement, `ts_type`, requested range, `retrieved_at`), even when empty.
  `request_url` is the exact URL from `response.request.gen_url()`: paste it in
  a browser to reproduce a read. Credentials are stripped and secret-looking
  query values (token, key, password, auth, sig) become `REDACTED`; the rest is
  byte for byte. The Processor should take `Source` from `origin["source_tag"]`.
- **Site code** lives in Hilltop's SiteInfo, tag `SecondSynonym` (shown as
  "Second Synonym" in Hilltop's UI). Horizons-specific, so the field is
  configurable (`site_code_field`).
- **Where to put a new question** (tested in order): can it be measurement
  metadata? site metadata? Only then a new protocol method. Name methods by the
  consumer's intent ("where do I resume?"), not by origin or mechanism.
- **`last_processed_time` rule.** Resume from the later of (a) the last standard
  point with a quality value and (b) the last quality-series entry, whatever its
  code (this picks up QC 100 "missing record" checkpoints). Quality 0 is a real
  NEMS code meaning unknown/unprocessed, so NaN and 0 both mean "no quality".
  A GetData with no range returns only the latest point (inferred from real
  responses; confirm), so it fetches the latest quality entry, then standard
  data with quality from that time forward. If quality has not changed for
  months that window is long; add a cap only if it proves slow. This replaces
  `utils.find_last_time`, which ignores quality.

## 8. Testing approach

- Provider tests use fake clients with the real client's methods (`get_data`,
  `base_url`, `hts_endpoint`, `response.request.gen_url()`), recording calls so
  tests can check what was *asked*, not only what came back. Fakes must also
  mirror the real client's **lifecycle**: once closed they refuse requests
  (`ClosableFake`). A fake that is more forgiving than the real thing hides bugs;
  that is exactly how the close-after-read bug passed every test.
- **Make fakes at least as awkward as the real thing.** Both bugs in the first
  live runs came from fakes being kinder than reality: clients that could be
  used after closing, and an empty range returned as an empty list rather than
  an error document. Whenever a live run disagrees with the fakes, change the
  fakes first, then fix the code (and check the new test fails on the old code).
- The live smoke script is the only check that fakes and reality agree. Run it
  after any change to the provider or whurl, and treat what it prints as the
  source of truth; when fakes and the script disagree, fix the fakes.
- Real XML (site info, check data, trimmed from live responses) is run through
  whurl's real parser, so field names and column behaviour can't drift.
- Paired tests: the real provider is checked against each narrow protocol it
  must satisfy (`ResolveProvider`, and every `DataProvider` method exists), so
  drift is caught from both sides.
- `ty` type-checks both source and tests.
- Prefer several plain tests to one loop over lambdas; prefer assertions that
  read without language trivia.

## 9. Dependencies we own: upstream work items

**Status: all done, none released.** Both are ours. whurl's fixes are on its main branch; Annalist's are on `fix-class-access`, not yet merged.

**Annalist** (`data-annalist`, branch `fix-class-access`, 1a3a029). Fixed:
`@ClassLogger` on a class method, static method, or any method reached through the
class (the owner class was dropped); the `params` field was wrong for every
class-logged method (it recorded `self` as the argument tuple, and flagged positional
arguments as `keyword`); decorated methods did not look like the methods written
(wrong signature, docstring and `ismethod` answers: issue #9); `@function_logger` on a
function with a keyword named `message`, `level` or `func` crashed after the function
ran; and annalizing `__init__` called the class's own `__repr__` before `__init__` had
run. Still open: static type checkers still see the decorator, not the method (needs
a `TYPE_CHECKING` declaration); the package lists `pytest`, `pytest-cov` and `twine`
as RUNTIME dependencies, which looks like a mistake; the 100% coverage gate has never
passed (83% upstream, 91% now). An issue exists for a tool-assisted rewrite.
Things to know: Annalist must be configured before any decorated code runs
(`Annalist().configure(...)`), so Processor tests configure it in a `conftest.py`.
The Processor is `Processor(run_config, provider)`, so the audit row for its
construction records the whole run config in `params`, and `site`, `from_date` and
`to_date` are found from instance attributes.

**whurl** (main, `77ce12a`). Fixed: a blank numeric value is NaN and a blank date is
`NaT` (it used to become `0.0` and 1940-01-01); `Quality` column name; the request
URL is attached to every error raised while reading a response (`error.url`), and a
body that is not XML is a `HilltopParseError`; a base URL with a trailing
slash, or an endpoint with a leading one, no longer gives `//`; the attribute
sanitiser handles several attributes per line and single-line XML (the old pattern
silently corrupted the `Interval` attributes of site info); an error document under
`<Hilltop>` no longer raises `KeyError`; and `HilltopResponseError` no longer says
"Parse error". An `I`-format item with fractional values (rainfall tips of 0.2) is
now kept as a float instead of truncated. **Unconfirmed:** whether a live server
really sends fractions under `I`; only a fixture does.
- Follow-up, not done: the provider's `_request_url_for` can use `error.url` and be
  deleted.
- Still open: profile interpolation (`interpolate_depth_profiles`) may need a whurl read.

**Findings in the OLD code (Python 3.14, pandas 3.0.5, numpy 2.5.3, the lock-file
versions).** *Correction: an earlier version of this section said five old tests fail,
and that two of them (`series_rounder`, `rainfall_six_minute_repacker`) "expect
warnings that no longer appear". That was wrong. Those two tests record warnings with
`warnings.catch_warnings(record=True)`, which an ambient `-W ignore` silences, and the
test runs that reported the failures had been given `-W ignore`. Run normally they
passed. Only three tests really failed.* The real findings, now fixed (the
`pandas3-fixes` patch):
- `utils.datetime_index_to_mowsecs` did `index.astype(np.int64) // 10**9`. pandas 3
  defaults to microsecond resolution (pandas 2: nanosecond), so every value was 1000
  times too small. It only ever worked on a nanosecond index, which is why it hid.
  Its only caller sets `Recorder Time` on check data. Tested at every resolution.
- `np.Inf` (`utils.py`, twice) and `np.NaN` (`rf_processor.py`) were removed in numpy 2.
  `np.Inf` sat in `compare_two_qc_take_min`, which the evaluator uses, so two tests failed.
- 10 uses of `pd.option_context("future.no_silent_downcasting", True)` and 9 of
  `infer_objects(copy=False)`. pandas 3 already behaves that way, so removing both is a
  no-op (checked on the eight shapes the code uses). pandas 4 would turn them into
  errors.
- `tasks.py`: a regex written as `'File\d+...'` (not a raw string), a `SyntaxWarning` in
  Python 3.14 that a later Python makes an error.
- The old `import_standard` cast values to `float32`; the new one keeps `float64`.

Guards so these don't come back: `pyproject.toml` turns every `Pandas4Warning` into a
test failure (for code a test runs), and `tests/test_python_compat.py` compiles every
package file with syntax warnings as errors and scans for numpy 2's removed names (for
code no test runs). The two warning tests now use `pytest.warns`, so they no longer
depend on the ambient warning filter.

**Not found, with the limits of the check.** A syntax-tree scan for copy-on-write
hazards (a name bound to a column or slice, then modified through that name, which
silently stops reaching the parent in pandas 3) found two candidates, both harmless
(`combine_comments`, `quality_encoder`). The scan cannot see aliasing through `self`
attributes or chained calls, and most Processor methods have no tests, so this is
**not** proof. The place to find any that exist is slice 4 (tests against the fake
provider). Also open: `horizons_source.py` casts to `datetime64[ns]` explicitly
(harmless alone, but whurl returns microseconds); and
`prototypes/atmospheric_pressure/hydrobot_run_ap.py` does not parse (line 34 is
`processor =`), an unfinished prototype from an earlier commit.

**Provider layer: verified live** (`scripts/try_provider_live.py`, three runs, dev whurl).
Behaviour and edge cases:
- `get_site_info`: `SecondSynonym` gives the code (e.g. `TCO`); the site metadata
  (69 fields) also carries things like `BARO_CLOSEST`, the associated baro site.
- `last_processed_time`: resumes at the real checkpoint, 2025-10-22 11:00.
- `get_quality` and `get_check` over a window with NO data: empty result plus a
  browser-pasteable `request_url`.
- A misspelled measurement or site name: an earlier version of this note said the
  server answers "No data", exactly as for a quiet period. **That was wrong**, and
  the provider's loose `No data` match encoded it, so a typo was treated as an
  empty range. The server's three answers differ (section 7) and are now told
  apart, each pinned by a test whose fixture is the pasted response.
  `last_processed_time` still returns `None` for all three, which makes `resolve`
  raise its helpful "check archive_standard_measurement_name" error instead of
  processing from the beginning. **Unconfirmed:** the exact wording the ARCHIVE
  uses for a never-archived measurement or a brand-new site.

The runs exposed three bugs in the provider, all fixed: clients closed after
every read; `Quality` arriving as text; empty range arriving as an error document.

Success paths (`--days 400 --show 3`):
- `get_standard`: 38,395 rows, `float64`, plausible values (998-1004 hPa), index
  `datetime64[us]` inside the requested window, no timezone shift; `datetime`
  arguments accepted.
- `get_quality`: 3 rows of `int64` codes (all 0). This reads the LIVE
  `RawLoggerNet.hts`, where raw data is quality 0 (unknown/unprocessed). The
  processed history (e.g. the QC 100 checkpoint at 2025-10-22 11:00) lives in
  the ARCHIVE, which only `last_processed_time` reads. Two different quality
  series; don't confuse them.
- `get_check`: `Check Pressure` `float64`, `Recorder Time` `datetime64[s]`,
  `Comment` pandas `string` (missing = `<NA>`). whurl's mowsecs conversion is
  correct: a 2025-12-15 13:40 check shows a Recorder Time of exactly
  2025-12-15 13:40:00.
- **Data oddity, not a provider bug:** the 2025-10-22 check record stores
  `Recorder Time` as `560418892`, which converts to 1957. Anything that uses
  Recorder Time must not trust it blindly (e.g. a plausibility check against the
  check's own timestamp).
- Mixed datetime resolutions: indexes are `datetime64[us]`, Recorder Time is
  `[s]`. Pandas copes; watch it when comparing or merging.

## 10. Processor rewrite (in progress)

Decisions: `Processor(run_config, provider)`; `depth` becomes `layer`; no parity with
the old constructor. Plan, in slices:

1. Constructor and `import_standard` **(done, below)**; then `import_quality`; then
   `import_check` (all via the provider; drop the second divisor division and the
   positional `item_info` loop).
2. `rf_processor` and `do_processor`.
3. Delete the `data_sources.py` match blocks and the depth parts of `tasks.py`.
4. Processor tests against a fake provider, replacing the live-server ones
   (`tests/test_processor.py`, `tests/test_web_integration.py`, which no longer import).

Keep the rewrite and any provenance redesign separate: don't change frame columns
during it.

**Slice 1 (done).** The pattern to repeat: the PURE half of an import lives in
`hydrobot/processors/importing.py` (provider answer in; frame and a list of `Note`s
out; no IO), and the Processor does the asking and reports the notes as processing
issues. `frames.py` holds the `EMPTY_*` frames (re-exported from `processor.py`).
- `Processor.__init__(run_config, provider)` reads nothing and opens nothing. Required
  keys: `site`, `standard_measurement_name`, `data_family`, `from_date`, `to_date`.
  Missing ones are all named in one `ValueError`. `from_date` must be before `to_date`.
  The config is deep-copied; unknown keys are ignored.
- `import_standard(site, measurement, from_date, to_date)` READS and RETURNS a frame,
  storing nothing (`do_processor` and `rf_processor` use it to fetch companion
  series). `load_data()` stores the run's own series, plus `standard_item_info`,
  `standard_origin` and an inferred `frequency`. `load_data` does standard only so far.
- An empty RANGE is reported as an error issue with the request URL, not raised. A
  wrong site or measurement name raises `DataProviderError` from the provider and
  stores nothing.
- `import_standard` takes per-call `frequency` and `infer_frequency`. Give neither
  and the run's settings apply; give either and the read's own replace them for that
  read only (`infer_frequency=False` alone means "as the server has it"). The
  callers need this: `do_processor` reads companion series with their own
  frequency, and `use_synthetic_data_from_alternative_site` reads another site
  irregularly.
- `use_synthetic_data_from_alternative_site` arrived from main with the merge and
  still called the old `import_standard` arguments. Updated, with tests. **After any
  merge from main, grep for callers of anything you changed.**
- Choices made, easy to reverse: `float64` (not `float32`); the "frequency given but
  `infer_frequency` on" warning is gone; fewer than 3 points with no frequency is a
  warning, not a crash; `defaults` and `interval_dict` default to `{}` (they were
  `None`); the old `from_config_yaml`-style classmethods are removed.

**Broken until later slices** (they read `_base_url`, `_standard_hts_filename` and
`_check_hts_filename`, which the Processor no longer has): `import_quality`,
`import_check`, `get_measurement_dataframe`, `interpolate_depth_profiles`,
`set_check_item_info_from_parameters`, and the properties `base_url`,
`standard_hts_filename`, `check_hts_filename`. `rf_processor` and `do_processor`
override or call methods that changed.

**`Recorder Time` (for `import_check`).** It is used: copied into check data and
exported to XML. Pass it through untouched, and have the Processor report a warning
(`report_processing_issue`) when it is implausibly far from the check's own time (one
live record says 1957). Whurl stays generic.

**Check data for layered runs.** It is interpolated from a depth profile, which
currently sits in Excel until an analyst uploads it to Hilltop. Open: hydrobot
imports the CSV itself, or requires the upload first. Either way it is one more
provider read, so the choice doesn't change the Processor. Proposed rule (**not yet
confirmed**): a run fetches check data only if it has a `check_measurement_name`;
layered families leave it out of their template and add profile-derived check
data explicitly in the script. This mirrors the old `depth is None` test.

## 11. Provenance and future drilldown plots

Frames today: standard (`Raw`, `Value`, `Changes`, `Remove`); check (+
`Recorder Time`, `Comment`, `Source`, `QC`); quality (`Raw`, `Value`, `Code`,
`Details`). Limit: `Changes` holds one code per point and each step overwrites
it, so earlier steps are lost. Direction (not a design): an append-only,
long-format change log (time, step, old, new) plus a steps table (method,
params, when), linkable to Annalist. Origin (section 7) is the first piece.

Questions a drilldown plot must answer: where did this value come from; what
happened to it step by step; why this QC code and from which rule; which check
data supported it; which processing issues overlap it; which run config and
software versions produced it.

## 12. Open decisions

- One batch = one data source? (inferred)
- Audit trail: Annalist versus the `setup:` header.
- Layered check data: CSV import versus a manual upload first.
- `ProcessingLog` protocol and a layer column in the SQL log (Nic owns the table).
- Batch loop: per-entry failure policy; generated scripts.
- A lone quality-series `0` entry returns that time instead of `None`:
  probably fine (it marks where unprocessed data begins); pin with a test
  whichever way is wanted.
- Where `scripts/` live and how they're documented (below).
- An empty standard RANGE is reported and the run continues. Should it stop the run?
  (Typos no longer look like this: they raise. What is left is a genuinely empty
  window.)
- Slice 2 needs an ARCHIVE standard read. `rf_processor` reads "historic" data
  from the archive hts and base URL; the provider has only `last_processed_time`
  for the archive.
- The old code's pandas 3 / numpy 2 problems (section 9) need fixing before the
  Processor's QC and export slices can be trusted.
- Linting: the repo's pre-commit pins ruff 0.4.3, black 24.4.2 and bandit; `processor.py`
  itself was not black-formatted before slice 1. Format it in its own commit.

## Working notes for whoever continues

- Never run the tests with `-W ignore` to quieten output: it silences the warnings that
  some tests record, and produces failures that are not real (it did exactly that here).
- Sandbox: the old caveats are out of date. Python 3.14 installs with
  `uv python install 3.14`, the lock-file versions install, and the dev whurl and
  Annalist install from their git branches, so real tests run (create the venv outside
  the repo). Use `--no-cov` (the 100% gate fails) and wrap anything that might touch a
  network in `timeout`; the old `test_web_integration.py` hangs. Only the author can
  run what needs the real server.
- Lint with the repo's pinned tools (`ruff==0.4.3`, `black==24.4.2`, `bandit==1.7.8`),
  not newer ones: the project enforces docstrings (pydocstyle) on tests too.
- A claim about what the server does must come from a pasted response, and get a
  test whose fixture IS that pasted text. The wrong "typo looks like no data" note
  survived for a long time because nothing in the code or tests contradicted it.
- Test practice that has paid off: fakes built from real parsed XML (not hand-made
  frames); a check that the fake equals the real provider's output
  (`tests/test_processors/test_with_the_real_provider.py`); and deliberately breaking
  the code to confirm the tests notice.
- Before building on a scratch checkout, check it is what you think it is. One of
  mine held unexplained, uncommitted changes that would otherwise have gone into a
  patch.
