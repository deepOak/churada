import logging

from .rule import Rule, CompositeRule
from .seedbox import Seedbox

# configure logfile
# logger levels: DEBUG, INFO


# build controller args
seedbox_rules = {}
seedbox_crules = {}

uname = "uname"
host = "host"
capacity = 359<<30
paths = {'remote_torrent':"~/deluge-watch",
         'remote_data':"~/files",
         'local_data':"/local_data_path"}
rules = {'download_valid':[],
         'download_path':[],
         'delete_valid':[]}
seedbox1_args = [uname,host,capacity,paths,rules]
seedbox1 = Seedbox(*seedbox1_args)

seedbox_list = [seedbox1]

controller_paths = {'local_torrent':"/active_torrent_path",
                    'local_invalid':"/invalid_torrent_path",
                    'local_watch':["/watch_path"]}


controller_rules = {'upload_path':[]}

controller_args = (seedbox_list,controller_paths,controller_rules)

# what we're actually building
options = {'controller_args':controller_args,
           'logfile':'/logpath',
           'loglevel':logging.INFO,
           'period':600, # period in seconds between actions
           'pidfile_path':'/var/run/churada/churada.pid'} 
