from churada.core import LocalTorrent,RemoteTorrent,Seedbox
from mock import MagicMock
import os

#def ltor_gen(name,path,size):
#    with 

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
    mock_ltor.move.side_effect = mock_ltor_move(mock_ltor,os.path.join(path,os.path.basename(mock_ltor.path)))
    return mock_ltor

rtor_template = """Name: $name
ID: $id
State: $state
Seeds: $cseed ($tseed) Peers: $cpeer ($tpeer) Availability: $avail
Size: $csize/$tsize Ratio: $ratio
Seed time: $stime Active: $atime
Tracker status: $tracker: $tracker_status"""

def rtor_gen(name=None,
             id='abcdef1234567890',
             state=None,
             cseed='5',
             tseed='10',
             cpeer='5',
             tpeer='10',
             avail='1.234',
             csize=None,
             tsize=None,
             ratio='1.234',
             stime='10000',
             atime='20000',
             tracker='tracker.com',
             tracker_status='Announce OK'):
    if not (name and state and tsize):
        return None
    if not csize or csize > tsize:
        csize = tsize
    rtor_data = rtor_template
    rtor_data.substitute(**locals())
    print rtor_data

rtor_gen(name='123',state='asdf',tsize=23)

def rtor_gen(name=None,state=None,size=None):
    mock_rtor = MagicMock(spec=RemoteTorrent)
    mock_rtor.name = name
    mock_rtor.state = state
    mock_rtor.size = size
#    mock_rtor.query.return_value = True
    mock_rtor.__eq__ = lambda self,other: self.name == other.name
    mock_rtor.__ne__ = lambda self,other: self.name != other.name
    mock_rtor.__nonzero__ = lambda self: bool(self.name) and bool(self.state)
    mock_rtor.__repr__ = lambda self: "<id: %s, name: %s, state:%s>" %(id(self),self.name,self.state)
    mock_rtor.__reduce__ = lambda self: (rtor_gen,(name,state))
    return mock_rtor
def seedbox_gen(capacity,free,upload_limit):
    mock_seedbox = MagicMock(spec=Seedbox)
    mock_seedbox.size = capacity - free
    mock_seedbox.free = free
    mock_seedbox.upload_limit = upload_limit
    mock_seedbox.capacity = capacity
    mock_seedbox.__repr__ = lambda self: "<seedbox: %d/%d (%d)>" %(self.free,self.capacity,self.upload_limit)
    return mock_seedbox

def mock_ltor_move(ltor,path):
    ltor.path = path

#def mock_ltor_parse(ltor,name=None,path=None):
#    ltor.name = name
#    ltor.path = path
#def mock_ltor_lambda(ltor,upd_args):
#    return lambda: mock_ltor_parse(ltor,**upd_args)

