# Performance and reliability review — 2026-11-10

The review covered the standalone HTML app, its identical GitHub Pages copy, the Python listing scraper, existing browser regressions, documentation, and the text-save/image-pack compatibility path. Existing features, cache formulas, reveal rules, save formats and personal data files are preserved. The two updated HTML files remain byte-identical.

Locations below refer to `geocache-field.html` in the source repository and the same lines in `index.html` in the Pages repository.

## Findings implemented

| Priority | Location | Issue and implemented correction |
| --- | --- | --- |
| High | `remapStageInputs`, line 997; startup migrations, line 3305 | Moving older answers between stages could reinterpret calculated answers as raw observations and apply transforms twice. Remapping now preserves legacy wrappers, and startup moves inputs before applying raw-input upgrades. Prior observations and recovery history remain available. |
| High | `stageMissingAnswers`, line 975 | Structured answers (multiple observations, selected digits and legacy calculated values) were converted to `[object Object]` before validation. Validation now uses their actual saved structure, accepts valid zero values, and rejects missing raw components. |
| High | `imgDel`, line 1371; cache/image removal handlers | Removing a cache or image could delete an IndexedDB blob still used by another cache or recovery record. References are removed first, then blobs are deleted only when no live cache, media archive or recovery version uses them. |
| Medium | Storage, line 381; live-input handler, line 2342 | Every keystroke serialized and synchronously stored the entire library. Edits now update memory immediately and coalesce writes over a maximum 200 ms interval. Blur, hiding the page, page exit and explicit save actions flush pending work. An abrupt browser/OS crash during that interval can still lose the newest unflushed edit. |
| Medium | `nearbyOrder`, line 715 | Sorting repeatedly parsed destinations and recalculated trigonometric distances inside its comparator. Each cache's destination and distance are now computed once per sort, preserving distance/name/code ordering. Sorting remains O(n log n); expensive distance calculation is O(n). |
| Medium | `routeMiles`, line 1629 | Trip mileage used posted coordinates while map markers used saved finals. Mileage now uses the same effective destinations as the map. Distances remain straight-line estimates. |
| Medium | `parseLoc`, line 416; `coordNum` | Impossible degree/minute values could become navigation destinations, and an oversized decimal latitude could be partially matched. Coordinate parsing now checks ranges, minute bounds and decimal-number boundaries. |
| Medium | `dmText`, line 423; `hav`, line 402 | Rounding could display 60.000 minutes without carrying into the degree. Rounding now carries correctly. Haversine input is clamped against floating-point overshoot near antipodal points. |
| Medium | `idb`, line 1346; `imgPut`, line 1363 | Concurrent cold image reads could open several database connections. Callers now share an opening promise, with failed-open retry and version-change cleanup. Aborted write transactions fall back to memory; successful writes clear stale fallback bytes. |
| Medium | `imgURL`, line 1376; `loadBitmap`, line 1389; image conversion | Image loading repeated IndexedDB reads, concurrent URL creation could leak URLs, and fallback bitmap URLs/decoded ImageBitmaps were not released. Reuse checks and explicit release now reduce redundant work and memory retention. Failed canvas conversion is handled explicitly. |
| Medium | `hydrateImages`, line 1424; `openViewer`, line 1442 | Completing an image load after its card/viewer was removed could dereference missing DOM nodes or interfere with a newer viewer. Detached results are ignored. |
| Medium | `startOrient`, line 1187; `startWake`, line 1199 | Delayed sensor permission or wake-lock responses could reactivate resources after closing the compass. Late results now check active navigation; unused/duplicate wake locks are released. |
| Medium | `gc_pull.py`, `parse_loc`, line 98; file reads/writes | The scraper accepted impossible coordinates and relied on OS-default text encoding. It now applies coordinate bounds and uses explicit UTF-8 for code lists, HTML dumps and JSON exports, preserving non-ASCII descriptions and emoji across platforms. |

## Validation

Final result: **20/20 regression scripts passed against each HTML version**. Both copies were tested independently using the same suite and are byte-identical.

The regression suite runs in Chromium and covers mobile/desktop map gestures, themes, navigation, stage completion, raw observations and formulas, owner messages, logging/undo, saved finals, file imports and portable backups. `test_optimizations.py` adds storage-write counts, linear distance lookups, structured completion, coordinate edge cases, shared-image deletion, delayed media/sensor responses and IndexedDB connection reuse. `test_scraper_validation.py` checks scraper coordinate bounds and text helpers offline.

Two older regression fixtures predated the current raw-input model. They now explicitly mark calculated values as legacy answers, separate calculation tests from scraped-final behavior, and place the checker cache in an explicit test trip. Their formula, missing-answer and migration assertions remain in place.

Measured checks: a synchronous burst of 100 input edits plus blur produces one durable library write; sorting 250 caches performs 250 destination lookups. The real image-pack round trip preserves all 141 available images byte-for-byte through import, reload and offline export. These are operation-count/data-integrity checks, not a claim of a particular wall-clock speedup on every device.

JavaScript syntax is checked with `node --check`; the scraper is compiled and its pure helpers tested without signing into Geocaching.

## Practical limits and future work

- Physical iOS/Android compass sensors and wake locks need real-device confirmation. Automated checks cover delayed permission/resource responses; live Geocaching scraping was not exercised because this session has no signed-in Geocaching state.
- The app still renders every cache card in the selected collection. For much larger libraries, incremental rendering and cached stage calculations would be the next performance project; implementing those requires separate gesture/focus/scroll testing.
- Progress still uses localStorage, so browser quota limits and simultaneous edits in multiple tabs remain architectural constraints. Existing storage warnings and portable exports remain available. Moving progress to IndexedDB or adding cross-tab conflict handling would be a separate migration.
- Gzip image packs still materialize their JSON and base64 payloads in memory. A binary/streaming backup format could lower peak memory, but would change the portable-file contract and needs a separately versioned migration.
- The source remains a single HTML file with some later function overrides. Consolidating modules and adding automatic mirror/CI checks would improve maintenance; this change keeps single-file distribution intact.
