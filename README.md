# Geocache Field Guide

Public browser app for GitHub Pages. **index.html is the sole maintained HTML source for the app.** This repository contains application code and public assets only. Personal saves and image packs are imported locally in the browser and are not published here.

Enable GitHub Pages in Settings → Pages → Deploy from a branch → main → /(root).

On first use, import your latest text save and image pack into the hosted site. Browser storage belongs to this site URL and browser/device. Normal HTML updates and refreshes preserve that storage. Keep exported backups; clearing browser data removes local saves. Reload the page to receive published updates.


See [PERFORMANCE-REVIEW.md](PERFORMANCE-REVIEW.md) for the performance and reliability fixes and their validation. There is no second maintained HTML copy. Make app changes here; private saves, photos, notes, image packs, and scraper workflows remain outside this public repository.

## Planning on the map

Plan starts with **All incomplete caches**, including caches already in lists. Unstarted markers are hollow; in-progress markers have their left half filled. A list’s emoji appears beside its caches. Choose a list to show only that trip’s numbered route. **Not in a list** remains available below the map.

Tap a marker to select it, then use **View cache details** to open Field. In the overview, **Add to list** opens a selector for your existing lists. With a trip selected, **Move to top of list** keeps its confirmation step. Removing a cache with ✕ in the reorder rows requires two taps within four seconds and offers Undo; the saved cache stays in your library. The corner icon fits the map to the current selection.

Opening details from the overview creates a persistent **Single cache view**. Editing, logging, switching tabs and reloading keep that cache open. Choose a collection or list in the menu to return to its Field view. Plan’s selection is saved separately from Field’s selection.

## Map regressions

Run `python tests/test_plan_map.py` with Playwright and Chromium installed (`CHROMIUM_PATH` defaults to `/usr/bin/chromium`). The test uses synthetic caches and blocks external requests. It covers desktop/mobile selection, list filtering, progress markers, dropdown assignment, persistent single-cache details, route edits, confirmation expiry, Undo, dragging, map gestures and empty states. It never reads personal saves or image packs.
