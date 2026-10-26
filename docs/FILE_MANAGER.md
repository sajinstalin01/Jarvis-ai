# JARVIS File & Folder Management

The local-first file manager is available through FeatureHub `fm` commands. It uses Python's standard library and does not upload file contents.

## Commands

- `fm dirs` — common Home, Desktop, Downloads, Documents, Pictures, Music, Videos and Temp paths.
- `fm list "<folder>"` — list a directory (up to 500 entries).
- `fm search "<root>" :: <glob-or-name>` — bounded filename search, e.g. `fm search "C:\\Users\\Rolex\\Downloads" :: *.pdf`.
- `fm search "<root>" :: content:<text>` — case-insensitive search in eligible text files; files over 1 MB and common binary formats are skipped.
- `fm create file "<path>"` / `fm create folder "<path>"`.
- `fm rename "<source>" :: "<destination>"`, `fm copy ...`, `fm move ...`. Existing destinations are never overwritten.
- `fm delete "<path>"` — preview and store a pending deletion, then run the exact `fm delete confirm "<path>"` shown. Drive roots, home, and current working directory are protected.
- `fm organize "<folder>" :: type|date|size` — preview moves into extension, modified-month, or size buckets. Run `fm organize confirm` to apply.
- `fm bulk-copy "<source glob>" :: "<existing destination folder>"` — copies matching files from one parent directory, up to 500; existing names are skipped.
- `fm zip "<file-or-folder>" :: "<new archive.zip>"`.
- `fm unzip "<archive.zip>" :: "<new-or-empty destination>"` — blocks ZIP path traversal and caps extraction at 10,000 entries / 2 GB expanded data.

## Safety and limits

Search skips hidden directories, symlinks, common build/cache folders and Windows system directories; it scans at most 2,500 files and returns at most 100 matches. This is bounded whole-root search, not Windows Search indexing or a full-text index. ZIP extraction validates member paths before extraction. Copy/move/rename refuse overwriting existing destinations. Delete and organize require explicit follow-up confirmation. Review the organization preview before confirming.
