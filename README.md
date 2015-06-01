Churada: 
A severe rain squall in the Mariana Islands (western Pacific Ocean) during the northeast monsoon; these squalls occur from November to April or May, but especially from January through March.

torrent file manager for remote seedboxes running deluge
- runs as a daemon process
- uploads torrents to seedboxes from local watchfolder
- upon completion, downloads torrent data
- gathers info from text output of deluge-console
- deletes torrents as necessary to free up server space for prospective .torrent upload files
 - deletions are prioritized based on performance, measured as ratio/time
 - deletions are limited based on individual specifications (e.g. minimum seedtime or ratio by tracker)
- supports custom download folders based on regex matching with deluge-console info
- supports custom upload seedbox based on regex matching with parsed *.torrent bencode
