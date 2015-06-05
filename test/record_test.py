#sys.path.insert(0,"/home/Brett/scripts/churada")
import unittest
from copy import deepcopy
from nose_parameterized import parameterized
from mock import MagicMock
from mock import patch
from mock import call

from churada.core import Seedbox
from churada.core import LocalRecord
from churada.core import RemoteRecord
from churada.core import LocalTorrent
from churada.core import RemoteTorrent
import time
import paramiko

def ltor_gen(name=None,path=None,size=None):
    mock_ltor = MagicMock(spec=LocalTorrent)
    mock_ltor.name = name
    mock_ltor.path = path
    mock_ltor.size = size
    mock_ltor.query.return_value = True
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
    mock_rtor.query.return_value = True
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

ltor_test = [ltor_gen(name=str(i),path=str(i),size=i) for i in range(0,5)]
ltor_elem = ltor_gen(name='5',path='5',size=5)
ltor_empty = ltor_gen(name='ltor_empty')

rtor_test = [rtor_gen(name=str(i),state=str(i),size=i) for i in range(0,5)]
rtor_elem = rtor_gen(name='5',state='5',size=5)

class LocalRecordTest(unittest.TestCase):
    def setUp(self):
        self.shell = MagicMock()
        self.lrec = LocalRecord(self.shell)
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
        self.lrec.record = control[:]
        self.lrec.ltor_add(**func_args)
        if append_flag:
            if 'pos' in func_args:
                control.insert(func_args['pos'],mock_ltor.return_value)
            else:
                control.append(mock_ltor.return_value)
        self.assertEqual(self.lrec.record,control)
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
        self.lrec.record = control[:]
        result = self.lrec.ltor_find(**func_args)
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
        self.lrec.record = control[:]
        if del_flag:
            self.lrec.record.insert(*ins_args)
        self.lrec.ltor_del(**func_args)
        self.assertEqual(self.lrec.record,control)
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
    @patch('churada.core.LocalTorrent')
    def ltor_update_test(self,_,control,func_args,upd_args,index,upd_flag,del_flag,mock_ltor):
        mock_ltor.return_value = ltor_gen(**upd_args)
        control = deepcopy(control)
        self.lrec.record = deepcopy(control)
        for ltor in self.lrec.record:
            ltor._LocalTorrent__parse.side_effect = mock_ltor_lambda(ltor,upd_args)
        if del_flag:
            del control[index]
        if upd_flag:
            mock_ltor_parse(control[index],**upd_args)
        self.lrec.ltor_update(**func_args)
        self.assertEquals(self.lrec.record,control)

class RemoteRecordTest(unittest.TestCase):
    def setUp(self):
        self.shell = MagicMock()
        self.rrec = RemoteRecord(self.shell)
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
        self.rrec.record = control[:]
        self.rrec.rtor_add(**func_args)
        if add_flag:
            if 'pos' in func_args:
                control.insert(func_args['pos'],func_args['rtor'])
            else:
                control.append(func_args['rtor'])
            self.assertEqual(self.rrec.shell.add_ssh.called,False)
        elif ssh_flag:
            pos = func_args['pos'] if 'pos' in func_args else None
            command = self.rrec.info_cmd %(func_args['name'])
            self.rrec.shell.add_ssh.assert_called_once()
        self.assertEqual(control,self.rrec.record)
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
        self.rrec.record = control[:]
        if del_flag:
            self.rrec.record.insert(*ins_args)
        self.rrec.rtor_del(**func_args)
        self.assertEqual(self.rrec.record,control)
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
        self.rrec.record = control[:]
        result = self.rrec.rtor_find(**func_args)
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
        self.rrec.rtor_add = MagicMock()
        control = control[:]
        self.rrec.record = control[:]
        self.rrec.rtor_update(**func_args)
        if del_flag:
            result = control[index]
            del control[index]
            self.rrec.rtor_add.assert_called_once_with(name=result.name,pos=index)
        else:
            self.assertEqual(self.rrec.rtor_add.called,False)
        self.assertEqual(control,self.rrec.record)

# first element in each has name,path/state = '5', size = 5
# implicit testing of iterator implementation of LocalRecord/RemoteRecord
down_list = [rtor_gen(name=str(i),state=str(i),size=i) for i in range(10,5,-1)]
up_list = [ltor_gen(name=str(i),path=str(i),size=i) for i in range(10,5,-1)]
info_list = [rtor_elem] + [rtor_gen(name=str(i),state=str(i),size=i) for i in range(20,5,-1)]
size = 185
paths = ("remote_torrent","remote_data","local_data")
rules = ([],[],[])
capacity = 200
uname = 'uname'
host = 'host'

class SeedboxTest(unittest.TestCase):
    def setUp(self):
        self.seedbox = Seedbox(uname,host,capacity,paths,rules)
        self.seedbox.shell = MagicMock()
        self.seedbox.up_queue.record = up_list
        self.seedbox.down_queue.record = down_list
        self.seedbox.info.record = info_list
        self.capacity = capacity
        self.size = size
    @parameterized.expand(
        [("zero_space",info_list,{'space':0,'rtor':None,'rtor_iter':None,'exitcode':None,'output':None},False),
         ("neg_space",info_list,{'space':-10,'rtor':None,'rtor_iter':None,'exitcode':None,'output':None},False),
         ("none_iter",info_list,{'space':10,'rtor':None,'rtor_iter':None,'exitcode':None,'output':None},True),
         ("delete_1",info_list,{'space':10,'rtor':None,'rtor_iter':iter(info_list),'exitcode':None,'output':None},True),
         ("delete_2",info_list,{'space':1,'rtor':None,'rtor_iter':iter(info_list),'exitcode':None,'output':None},True),
         ("delete_delete",info_list,{'space':6,'rtor':rtor_elem,'rtor_iter':iter(info_list),'exitcode':0,'output':None},True),
         ("delete_nodelete",info_list,{'space':5,'rtor':rtor_elem,'rtor_iter':iter(info_list),'exitcode':0,'output':None},False),
         ("nodelete_delete",info_list,{'space':5,'rtor':rtor_elem,'rtor_iter':iter(info_list),'exitcode':1,'output':None},True)]
       )
    def delete_test(self,_,control,func_args,call_flag): #rtor,rtor_iter,output,exitcode,call_flag):
        # setup expected arguments
        rtor_iter_ = iter(control)
        rtor_ = rtor_iter_.next()
        command_ = self.seedbox._Seedbox__delete_command %(rtor_.name)
        func_ = self.seedbox.delete
        space_ = func_args['space']
        if func_args['rtor'] and func_args['exitcode'] == 0:
            space_ -= func_args['rtor'].size
        args_ = {'rtor':rtor_,'space':space_}
        self.seedbox.delete(**func_args)
        if call_flag:
            self.seedbox.shell.add_ssh.assert_called_once()
            call_args,call_kwargs = self.seedbox.shell.add_ssh.call_args
            command,func,args = call_args
            rtor_iter = args.pop('rtor_iter')
            # check arguments are the same
            self.assertEqual(command,command_)
            self.assertEqual(func,func_)
            self.assertEqual(args,args_)
            # check that iterators are the same
            for rtor,rtor_ in zip(rtor_iter,rtor_iter_):
                self.assertEqual(rtor,rtor_)
        else:
            self.assertEqual(self.seedbox.shell.add_ssh.called,False)
    @parameterized.expand(
       [("zero_space",down_list,None,{'space':0,'rtor':None,'rtor_iter':None,'exitcode':None,'output':None},False),
        ("neg_space",down_list,None,{'space':-10,'rtor':None,'rtor_iter':None,'exitcode':None,'output':None},False),
        ("none_iter",down_list,down_list[0],{'space':10,'rtor':None,'rtor_iter':None,'exitcode':None,'output':None},True),
        ("download_1",down_list,down_list[0],{'space':10,'rtor':None,'rtor_iter':iter(down_list),'exitcode':None,'output':None},True),
        ("download_2",down_list,None,{'space':1,'rtor':None,'rtor_iter':iter(down_list),'exitcode':None,'output':None},False),
        ("download_3",down_list,down_list[1],{'space':9,'rtor':None,'rtor_iter':iter(down_list),'exitcode':None,'output':None},True),
        ("download_4",down_list,down_list[2],{'space':8,'rtor':None,'rtor_iter':iter(down_list),'exitcode':None,'output':None},True),
        ("download_5",down_list,down_list[4],{'space':6,'rtor':None,'rtor_iter':iter(down_list),'exitcode':None,'output':None},True),
        ("download_download",down_list,down_list[1],{'space':14,'rtor':rtor_elem,'rtor_iter':iter(down_list),'exitcode':0,'output':None},True),
        ("download_nodownload",down_list,None,{'space':7,'rtor':rtor_elem,'rtor_iter':iter(down_list),'exitcode':0,'output':None},False),
        ("nodownload_download",down_list,down_list[3],{'space':7,'rtor':rtor_elem,'rtor_iter':iter(down_list),'exitcode':1,'output':None},True)])
    def download_test(self,_,control,rtor_control,func_args,call_flag):
        rtor_iter_ = iter(control)
        rtor_ = rtor_iter_.next()
        while rtor_control and rtor_ != rtor_control:
            rtor_ = rtor_iter_.next()
        download_path = self.seedbox._Seedbox__check_download_path(rtor_)
        command_ = self.seedbox._Seedbox__download_command %(self.seedbox.path_remote_data,download_path)
        func_ = self.seedbox.download
        space_ = func_args['space']
        if func_args['rtor'] and func_args['exitcode'] == 0:
            space_ -= func_args['rtor'].size
        args_ = {'rtor':rtor_,'space':space_}
        self.seedbox.download(**func_args)
        if call_flag:
            self.seedbox.shell.add_shell.assert_called_once()
            call_args,call_kwargs = self.seedbox.shell.add_shell.call_args
            command,func,args = call_args
            rtor_iter = args.pop('rtor_iter')
            self.assertEqual(command,command_)
            self.assertEqual(func,func_)
            self.assertEqual(args,args_)
            for rtor,rtor_ in zip(rtor_iter,rtor_iter_):
                self.assertEqual(rtor,rtor_)
        else:
            self.assertEqual(self.seedbox.shell.add_shell.called,False)

# have yet to write this function
#    def enqueue_test(self):
#        pass
# trivial method - shouldn't need testing
#    def update_test(self):
#        pass

    @parameterized.expand(
       [("zero_space",up_list,None,{'space':0,'ltor':None,'ltor_iter':None,'exitcode':None,'output':None},False),
        ("neg_space",up_list,None,{'space':-10,'ltor':None,'ltor_iter':None,'exitcode':None,'output':None},False),
        ("none_iter",up_list,up_list[0],{'space':10,'ltor':None,'ltor_iter':None,'exitcode':None,'output':None},True),
        ("upload_1",up_list,up_list[0],{'space':10,'ltor':None,'ltor_iter':iter(up_list),'exitcode':None,'output':None},True),
        ("upload_2",up_list,None,{'space':1,'ltor':None,'ltor_iter':iter(up_list),'exitcode':None,'output':None},False),
        ("upload_3",up_list,up_list[1],{'space':9,'ltor':None,'ltor_iter':iter(up_list),'exitcode':None,'output':None},True),
        ("upload_4",up_list,up_list[2],{'space':8,'ltor':None,'ltor_iter':iter(up_list),'exitcode':None,'output':None},True),
        ("upload_5",up_list,up_list[4],{'space':6,'ltor':None,'ltor_iter':iter(up_list),'exitcode':None,'output':None},True),
        ("upload_upload",up_list,up_list[1],{'space':14,'ltor':ltor_elem,'ltor_iter':iter(up_list),'exitcode':0,'output':None},True),
        ("upload_upload",up_list,None,{'space':7,'ltor':ltor_elem,'ltor_iter':iter(up_list),'exitcode':0,'output':None},False),
        ("noupload_upload",up_list,up_list[3],{'space':7,'ltor':ltor_elem,'ltor_iter':iter(up_list),'exitcode':1,'output':None},True)])
    def upload_test(self,_,control,ltor_control,func_args,call_flag):
        ltor_iter_ = iter(control)
        ltor_ = ltor_iter_.next()
        while ltor_control and ltor_ != ltor_control:
            ltor_ = ltor_iter_.next()
        command_ = self.seedbox._Seedbox__upload_command %(ltor_.path,self.seedbox.path_remote_torrent)
        func_ = self.seedbox.upload
        space_ = func_args['space']
        if func_args['ltor'] and func_args['exitcode'] == 0:
            space_ -= func_args['ltor'].size
        args_ = {'ltor':ltor_,'space':space_}
        self.seedbox.upload(**func_args)
        if call_flag:
            self.seedbox.shell.add_shell.assert_called_once()
            call_args,call_kwargs = self.seedbox.shell.add_shell.call_args
            command,func,args = call_args
            ltor_iter = args.pop('ltor_iter')
            self.assertEqual(command,command_)
            self.assertEqual(func,func_)
            self.assertEqual(args,args_)
            for ltor,ltor_ in zip(ltor_iter,ltor_iter_):
                self.assertEqual(ltor,ltor_)
        else:
            self.assertEqual(self.seedbox.shell.add_shell.called,False)

