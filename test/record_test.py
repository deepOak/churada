#sys.path.insert(0,"/home/Brett/scripts/churada")
import unittest
from copy import deepcopy
from nose_parameterized import parameterized
from mock import MagicMock
from mock import patch

from churada.core import Record
from churada.core import LocalTorrent
from churada.core import RemoteTorrent
import time
import paramiko

def ltor_gen(name=None,path=None):
    mock_ltor = MagicMock(spec=LocalTorrent)
    mock_ltor.name = name
    mock_ltor.path = path
    mock_ltor.__eq__ = lambda self,other: self.name == other.name or self.path == other.path
    mock_ltor.__ne__ = lambda self,other: self.name != other.name and self.path != other.path
    mock_ltor.__nonzero__ = lambda self: bool(self.path) and bool(self.name)
    mock_ltor.__repr__ = lambda self: "<id: %s, name: %s, path:%s>"%(id(self),self.name,self.path)
    mock_ltor.__reduce__ = lambda self: (ltor_gen,(name,path))
    return mock_ltor
def rtor_gen(name=None,state=None):
    mock_rtor = MagicMock(spec=RemoteTorrent)
    mock_rtor.name = name
    mock_rtor.state = state
    mock_rtor.__eq__ = lambda self,other: self.name == other.name
    mock_rtor.__ne__ = lambda self,other: self.name != other.name
    mock_rtor.__nonzero__ = lambda self: bool(self.name) and bool(self.state)
    mock_rtor.__repr__ = lambda self: "<id: %s, name: %s, state:%s>" %(id(self),self.name,self.state)
    mock_rtor.__reduce__ = lambda self: (rtor_gen,(name,state))
    return mock_rtor
def mock_ltor_parse(ltor,name=None,path=None):
    ltor.name = name
    ltor.path = path
def mock_ltor_lambda(ltor,upd_args):
    return lambda: mock_ltor_parse(ltor,**upd_args)

ltor_test = [ltor_gen(name=str(i),path=str(i)) for i in range(0,5)]
ltor_elem = ltor_gen(name='5',path='5')
ltor_empty = ltor_gen(name='ltor_empty')

rtor_test = [rtor_gen(name=str(i),state=str(i)) for i in range(0,5)]
rtor_elem = rtor_gen(name='5',state='5')

class RecordTest(unittest.TestCase):
    def setUp(self):
        self.shell = MagicMock()
        self.record = Record(self.shell)
    @parameterized.expand(
       [("empty_args",ltor_test,{},{},False),
        ("empty_object_1",ltor_test,{'ltor':ltor_gen(name='ltor_empty')},{},False),
        ("empty_object_2",ltor_test,{'ltor':ltor_gen(path='ltor_empty')},{},False),
        ("empty_path",ltor_test,{'path':''},{},False),
        ("duplicate_object",ltor_test,{'ltor':ltor_test[3]},{},False),
        ("duplicate_path_1",ltor_test,{'path':'3'},{},False),
        ("duplicate_path_2",ltor_test,{'ltor':ltor_gen(path=str(4))},{},False),
        ("unique_object",ltor_test,{'ltor':ltor_elem},{'name':'5','path':'5'},True),
        ("unique_path",ltor_test,{'path':'5'},{'name':'5','path':'5'},True),
        ("insert",ltor_test,{'ltor':ltor_elem,'pos':2},{'name':'5','path':'5'},True),
        ("arg_priority",ltor_test,{'ltor':ltor_elem,'path':'6'},{'name':'5','path':'5'},True)]
        )
    @patch('churada.core.LocalTorrent')
    @patch('time.time')
    def ltor_add_test(self,_,control,func_args,obj_args,append_flag,mock_time,mock_ltor):
        mock_ltor.return_value = ltor_gen(**obj_args)
        control = control[:]
        self.record.record_local = control[:]
        self.record.ltor_add(**func_args)
        if append_flag:
            if 'pos' in func_args:
                control.insert(func_args['pos'],mock_ltor.return_value)
            else:
                control.append(mock_ltor.return_value)
        self.assertEqual(self.record.record_local,control)
    @parameterized.expand(
       [("empty_args",ltor_test,{},None),
        ("present_name",ltor_test,{'name':'3'},ltor_test[3]),
        ("present_path",ltor_test,{'path':'2'},ltor_test[2]),
        ("present_object",ltor_test,{'ltor':ltor_test[4]},ltor_test[4]),
        ("equal_object_1",ltor_test,{'ltor':ltor_gen(name='4',path='not 4')},ltor_test[4]),
        ("equal_object_2",ltor_test,{'ltor':ltor_gen(name='not 4',path = '4')},ltor_test[4]),
        ("absent_name",ltor_test,{'name':'5'},None),
        ("absent_path",ltor_test,{'path':'5'},None),
        ("absent_object",ltor_test,{'ltor':ltor_gen(name='5',path='5')},None),
        ("arg_priority_1",ltor_test,{'ltor':ltor_test[3],'name':'4','path':'2'},ltor_test[3]),
        ("arg_priority_2",ltor_test,{'ltor':ltor_test[3],'name':'4'},ltor_test[3]),
        ("arg_priority_3",ltor_test,{'ltor':ltor_test[3],'path':'4'},ltor_test[3]),
        ("arg_priority_4",ltor_test,{'name':'3','path':'4'},ltor_test[3])]
       )
    def ltor_find_test(self,_,control,func_args,return_val):
        self.record.record_local = control[:]
        result = self.record.ltor_find(**func_args)
        self.assertEqual(result,return_val)
    @parameterized.expand(
       [("empty_args",ltor_test,{},[],False),
        ("empty_object",ltor_test,{'ltor':ltor_gen(name='ltor_empty')},[],False),
        ("empty_path",ltor_test,{'path':''},[],False),
        ("empty_name",ltor_test,{'name':''},[],False),
        ("present_object",ltor_test,{'ltor':ltor_elem},[3,ltor_elem],True),
        ("present_path",ltor_test,{'path':'5'},[3,ltor_elem],True),
        ("present_name",ltor_test,{'name':'5'},[3,ltor_elem],True),
        ("absent_name",ltor_test,{'name':'6'},[],False),
        ("absent_path",ltor_test,{'path':'6'},[],False),
        ("absent_object",ltor_test,{'ltor':ltor_elem},[],False),
        ("arg_priority_1",ltor_test,{'ltor':ltor_elem,'name':'3','path':'2'},[3,ltor_elem],True),
        ("arg_priority_2",ltor_test,{'ltor':ltor_elem,'name':'3'},[3,ltor_elem],True),
        ("arg_priority_3",ltor_test,{'ltor':ltor_elem,'path':'3'},[3,ltor_elem],True),
        ("arg_priority_4",ltor_test,{'name':'5','path':'4'},[3,ltor_elem],True)]
       )
    def ltor_del_test(self,_,control,func_args,ins_args,del_flag):
        self.record.record_local = control[:]
        if del_flag:
            self.record.record_local.insert(*ins_args)
        self.record.ltor_del(**func_args)
        self.assertEqual(self.record.record_local,control)
    @parameterized.expand(
       [("empty_args",ltor_test,{},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("empty_obj",ltor_test,{'ltor':ltor_gen(name='ltor_empty')},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("empty_name",ltor_test,{'name':''},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("empty_path",ltor_test,{'path':''},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("present_obj",ltor_test,{'ltor':ltor_test[1]},{'name':'upd_name','path':'upd_path'},1,True,False),
        ("present_name",ltor_test,{'name':'1'},{'name':'upd_name','path':'upd_path'},1,True,False),
        ("present_path",ltor_test,{'name':'1'},{'name':'upd_name','path':'upd_path'},1,True,False),
        ("absent_obj",ltor_test,{'ltor':ltor_elem},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("absent_name",ltor_test,{'name':'5'},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("absent_path",ltor_test,{'path':'5'},{'name':'upd_name','path':'upd_path'},1,False,False),
        ("empty_name_update",ltor_test,{'name':'1'},{'name':'','path':'upd_path'},1,False,True),
        ("empty_path_update",ltor_test,{'path':'1'},{'name':'upd_name','path':''},1,False,True),
        ("arg_priority_1",ltor_test,{'ltor':ltor_test[1],'name':'2','path':'3'},{'name':'upd_name','path':'upd_path'},1,True,False),
        ("arg_priority_2",ltor_test,{'ltor':ltor_test[1],'name':'2'},{'name':'upd_name','path':'upd_path'},1,True,False),
        ("arg_priority_3",ltor_test,{'ltor':ltor_test[1],'path':'3'},{'name':'upd_name','path':'upd_path'},1,True,False),
        ("arg_priority_4",ltor_test,{'name':'2','path':'3'},{'name':'upd_name','path':'upd_path'},2,True,False)]
       )
    def ltor_update_test(self,_,control,func_args,upd_args,index,upd_flag,del_flag):
        control = deepcopy(control)
        self.record.record_local = deepcopy(control)
        for ltor in self.record.record_local:
            ltor.parse.side_effect = mock_ltor_lambda(ltor,upd_args)
        if del_flag:
            del control[index]
        if upd_flag:
            mock_ltor_parse(control[index],**upd_args)
        self.record.ltor_update(**func_args)
        self.assertEquals(self.record.record_local,control)
    @parameterized.expand(
       [("empty_args",rtor_test,{},False,False),
        ("empty_obj_1",rtor_test,{'rtor':rtor_gen(name='empty_rtor',state='')},False,False),
        ("empty_obj_2",rtor_test,{'rtor':rtor_gen(name='',state='empty_rtor')},False,False),
        ("empty_name",rtor_test,{'name':''},False,False),
        ("present_obj",rtor_test,{'rtor':rtor_gen(name='1',state='state')},False,False),
        ("present_name",rtor_test,{'name':'1'},False,False),
        ("absent_obj",rtor_test,{'rtor':rtor_elem},False,True),
        ("absent_name",rtor_test,{'name':'5'},True,False),
        ("arg_priority",rtor_test,{'rtor':rtor_elem,'name':'5'},False,True)]
       )
    def rtor_add_test(self,_,control,func_args,ssh_flag,add_flag):
        control = control[:]
        self.record.record_remote = control[:]
        self.record.rtor_add(**func_args)
        if add_flag:
            if 'pos' in func_args:
                control.insert(func_args['pos'],func_args['rtor'])
            else:
                control.append(func_args['rtor'])
            self.assertEqual(self.record.shell.add_ssh.called,False)
        elif ssh_flag:
            pos = func_args['pos'] if 'pos' in func_args else None
            command = self.record.info_cmd %(func_args['name'])
            func = self.record._Record__rtor_add
            self.record.shell.add_ssh.assert_called_once_with(command,func,{'pos':pos})
        self.assertEqual(control,self.record.record_remote)
    @parameterized.expand(
       [("empty_args",rtor_test,{},[],False),
        ("empty_obj_1",rtor_test,{'rtor':rtor_gen(name='empty_rtor',state='')},[],False),
        ("empty_obj_2",rtor_test,{'rtor':rtor_gen(name='',state='empty_rtor')},[],False),
        ("empty_name",rtor_test,{'name':''},[],False),
        ("present_obj",rtor_test,{'rtor':rtor_elem},[3,rtor_elem],True),
        ("present_name",rtor_test,{'name':'5'},[3,rtor_elem],True),
        ("absent_obj",rtor_test,{'rtor':rtor_elem},[],False),
        ("absent_name",rtor_test,{'name':'5'},[],False),
        ("arg_priority",rtor_test,{'rtor':rtor_elem,'name':'2'},[2,rtor_elem],True)]
       )
    def rtor_del_test(self,_,control,func_args,ins_args,del_flag):
        self.record.record_remote = control[:]
        if del_flag:
            self.record.record_remote.insert(*ins_args)
        self.record.rtor_del(**func_args)
        self.assertEqual(self.record.record_remote,control)
    @parameterized.expand(
       [("empty_args",rtor_test,{},None),
        ("empty_name",rtor_test,{'name':''},None),
        ("empty_obj_1",rtor_test,{'rtor':rtor_gen(name='1',state='')},None),
        ("empty_obj_2",rtor_test,{'rtor':rtor_gen(name='',state='1')},None),
        ("present_obj",rtor_test,{'rtor':rtor_test[2]},rtor_test[2]),
        ("present_name",rtor_test,{'name':'2'},rtor_test[2]),
        ("equal_obj",rtor_test,{'rtor':rtor_gen(name='2',state='not 2')},rtor_test[2]),
        ("absent_obj",rtor_test,{'rtor':rtor_elem},None),
        ("absent_name",rtor_test,{'name':'5'},None),
        ("arg_priority",rtor_test,{'rtor':rtor_test[2],'name':'4'},rtor_test[2])]
       )
    def rtor_find_test(self,_,control,func_args,return_value):
        self.record.record_remote = control[:]
        result = self.record.rtor_find(**func_args)
        self.assertEqual(result,return_value)
    @parameterized.expand(
       [("empty_args",rtor_test,{},None,False),
        ("empty_obj_1",rtor_test,{'rtor':rtor_gen(name='1',state='')},None,False),
        ("empty_obj_2",rtor_test,{'rtor':rtor_gen(name='',state='1')},None,False),
        ("present_obj",rtor_test,{'rtor':rtor_test[1]},1,True),
        ("present_name",rtor_test,{'name':'1'},1,True),
        ("absent_obj",rtor_test,{'rtor':rtor_elem},None,False),
        ("absent_name",rtor_test,{'name':'5'},None,False),
        ("arg_priority",rtor_test,{'rtor':rtor_test[1],'name':'2'},1,True)] 
       )
    def rtor_update_test(self,_,control,func_args,index,del_flag):
        self.record.rtor_add = MagicMock()
        control = control[:]
        self.record.record_remote = control[:]
        self.record.rtor_update(**func_args)
        if del_flag:
            result = control[index]
            del control[index]
            self.record.rtor_add.assert_called_once_with(name=result.name,pos=index)
        else:
            self.assertEqual(self.record.rtor_add.called,False)
        self.assertEqual(control,self.record.record_remote)
