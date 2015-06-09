from churada.core import LocalTorrent,RemoteTorrent
from mock import MagicMock

def ltor_gen(name=None,path=None,size=None):
    mock_ltor = MagicMock(spec=LocalTorrent)
    mock_ltor.name = name
    mock_ltor.path = path
    mock_ltor.size = size
#    mock_ltor.query.return_value = True
    mock_ltor.__eq__ = lambda self,other: self.name == other.name or self.path == other.path
    mock_ltor.__ne__ = lambda self,other: self.name != other.name and self.path != other.path
    mock_ltor.__nonzero__ = lambda self: bool(self.path) and bool(self.name)
    mock_ltor.__repr__ = lambda self: "<id: %s, name: %s, path:%s>"%(id(self),self.name,self.path)
    mock_ltor.__reduce__ = lambda self: (ltor_gen,(name,path))
    return mock_ltor
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
#def mock_ltor_parse(ltor,name=None,path=None):
#    ltor.name = name
#    ltor.path = path
#def mock_ltor_lambda(ltor,upd_args):
#    return lambda: mock_ltor_parse(ltor,**upd_args)

