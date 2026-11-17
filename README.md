# Geocache Field Guide

Public browser app for GitHub Pages. **index.html is the sole maintained HTML source for the app.** This repository contains application code and public assets only. Personal saves and image packs are imported locally in the browser and are not published here.

Enable GitHub Pages in Settings → Pages → Deploy from a branch → main → /(root).

On first use, import your latest text save and image pack into the hosted site. Browser storage belongs to this site URL and browser/device. Normal HTML updates and refreshes preserve that storage. Keep exported backups; clearing browser data removes local saves. Reload the page to receive published updates.


See [PERFORMANCE-REVIEW.md](PERFORMANCE-REVIEW.md) for the performance and reliability fixes and their validation. There is no second maintained HTML copy. Make app changes here; private saves, photos, notes, image packs, and scraper workflows remain outside this public repository.

## Planning on the map

Plan starts with **All caches**, including completed caches and caches already in lists. **In progress** and **Not started** use the same automatic unlisted collections as the sidebar. Unstarted markers are hollow; in-progress markers have their left half filled. A list’s emoji appears over its cache’s colored shape. Completed map markers carry a green check badge at the lower right. Choose a list to show only that trip’s numbered route. **Not in a list** remains available below the map.

Tap a marker to select it, then use **View cache details** to open Field. Double-tapping the same marker opens that same view directly, or jumps to the cache within the selected trip. In the overview, **Add to list** is a dropdown selector for your existing lists. Cache titles open Field details; listed rows show their memberships and a Manage lists dropdown. Selecting a list adds or removes that membership and offers Undo. Completed rows show a green label and check badge. With a trip selected, **Move to top of list** keeps its confirmation step. Selected-list rows use the same type icons and text formatting as overview rows, with compact grabber spacing. Removing a cache with ✕ in the reorder rows requires two taps within four seconds and offers Undo. Tapping outside a pending list-removal, saved-cache-removal or move-to-top confirmation cancels it; the saved cache stays in your library. The map keeps a square frame for vertical, horizontal and clustered routes; its bounds expand along the longer route axis to keep every cache visible. The corner icon restores the tight initial map framing. The muted GC code follows the title; type and distance are separated by a dot. Progress and completion status always appear on a separate row beneath cache details and distance. The nearby refresh control is an icon at the top right.

Opening details from the overview creates a persistent **Single cache view**. Editing, logging, switching tabs and reloading keep that cache open. Choose a collection or list in the menu to return to its Field view. Changing the Plan filter also selects that list or the all-cache overview in Field.

## Map regressions

Run `python tests/test_plan_map.py` with Playwright and Chromium installed (`CHROMIUM_PATH` defaults to `/usr/bin/chromium`). The test uses synthetic caches and blocks external requests. It covers desktop/mobile selection, list filtering, progress markers, dropdown assignment, persistent single-cache details, route edits, confirmation expiry, Undo, dragging, map gestures and empty states. It never reads personal saves or image packs.
