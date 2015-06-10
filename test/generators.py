from mock import MagicMock, patch, mock_open
from string import Template
import os

from churada.torrent import RemoteTorrent,RemoteTorrentError
from churada.torrent import LocalTorrent,LocalTorrentError
from churada.seedbox import Seedbox

#def ltor_gen(name,path,size):
#    with 

def seedbox_gen(*args,**kwargs):
#    return Seedbox(*args,**kwargs)
    pass

def ltor_gen(name=None,path=None,size=None):
    mock_ltor = MagicMock(spec=LocalTorrent)
    mock_ltor.name = name
    mock_ltor.path = path
    mock_ltor.size = size
#    mock_ltor.query.return_value = True
    mock_ltor.__eq__ = lambda self,other: self.name == other.name or self.path == other.path
    mock_ltor.__ne__ = lambda self,other: self.name != other.name and self.path != other.path
    mock_ltor.__nonzero__ = lambda self: bool(self.path) and bool(self.name)
    mock_ltor.__repr__ = lambda self: "<id: %s, name: %s, path:%s,size=%s>"%(id(self),self.name,self.path,self.size)
    mock_ltor.__reduce__ = lambda mock_ltor: (ltor_gen,(name,path,size))
#    mock_ltor.move.side_effect = mock_ltor_move(mock_ltor,os.path.join(path,os.path.basename(mock_ltor.path)))
    return mock_ltor

rtor_template = Template("""Name: $name
ID: $id
State: $state Up Speed: $uspeed/s
Seeds: $cseed ($tseed) Peers: $cpeer ($tpeer) Availability: $avail
Size: $csize/$size Ratio: $ratio
Seed time: $stime Active: $atime
Tracker status: $tracker: $tracker_status""")

def rtor_gen(name,
             state,
             id='abcdef1234567890',
             uspeed='53',
             cseed='5',
             tseed='10',
             cpeer='5',
             tpeer='10',
             avail='1.234',
             csize=None,
             size='1024',
             ratio='1.234',
             stime='10000',
             atime='20000',
             tracker='tracker.com',
             tracker_status='Announce OK'):
    if not csize or csize > size:
        csize = size
    rtor_data = rtor_template.substitute(**locals())
    timestamp = 12345
    return RemoteTorrent(rtor_data,timestamp)

ltor_template = Template("""d8:announce${announcelen}:${announce}4:infod4:name${namelen}:${name}6:lengthi${size}e6:pieces0:12:piece lengthi${piece_length}eee""")

def ltor_gen(name,
             path,
             announce='http://www.tracker.com',
             size=1024,
             piece_length='524288'):
    ltor_data = ltor_template.substitute(announcelen=len(announce),
                                         announce=announce,
                                         namelen=len(name),
                                         name=name,
                                         size=size,
                                         piece_length=piece_length)
    patcher_isfile = patch('os.path.isfile',return_value=True)
    patcher_getsize = patch('os.path.getsize',return_value=0)
    patcher_open = patch("__builtin__.open",mock_open(read_data=ltor_data))
    patcher_isfile.start()
    patcher_getsize.start()
    patcher_open.start()

    ltor = LocalTorrent(path)

    patch.stopall()
    return ltor



#def ltor_gen(name=None,

#def mock_ltor_parse(ltor,name=None,path=None):
#    ltor.name = name
#    ltor.path = path
#def mock_ltor_lambda(ltor,upd_args):
#    return lambda: mock_ltor_parse(ltor,**upd_args)

