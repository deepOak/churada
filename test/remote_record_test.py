import unittest
from nose_parameterized import parameterized
from mock import MagicMock,patch

from churada.record import LocalRecord,RemoteRecord
from churada.torrent import LocalTorrent,RemoteTorrent

from generators import ltor_gen,rtor_gen

rtor_test = [rtor_gen(name=str(i),state=str(i),size=i) for i in range(0,5)]
rtor_elem = rtor_gen(name='5',state='5',size=5)

class RemoteRecordTest(unittest.TestCase):
    def setUp(self):
        self.shell = MagicMock()
        self.rrec = RemoteRecord(self.shell)
    @parameterized.expand(
       [("empty_args",rtor_test,{},False,False),
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
        ("present_obj",rtor_test,{'rtor':rtor_test[2]},rtor_test[2]),
        ("present_name",rtor_test,{'name':'2'},rtor_test[2]),
        ("equal_obj",rtor_test,{'rtor':rtor_gen(name='2',state='not2')},rtor_test[2]),
        ("absent_obj",rtor_test,{'rtor':rtor_elem},None),
        ("absent_name",rtor_test,{'name':'5'},None),
        ("arg_priority",rtor_test,{'rtor':rtor_test[2],'name':'4'},rtor_test[2])]
       )
    def rtor_find_test(self,_,control,func_args,return_value):
        self.rrec.record = control[:]
        result = self.rrec.rtor_find(**func_args)
        self.assertEqual(result,return_value)
#    @parameterized.expand(
#       [("empty_args",rtor_test,{},None,False),
#        ("present_obj",rtor_test,{'rtor':rtor_test[1]},1,True),
#        ("present_name",rtor_test,{'name':'1'},1,True),
#        ("absent_obj",rtor_test,{'rtor':rtor_elem},None,False),
#        ("absent_name",rtor_test,{'name':'5'},None,False),
#        ("arg_priority",rtor_test,{'rtor':rtor_test[1],'name':'2'},1,True)] 
#       )
#    def rtor_update_test(self,_,control,func_args,index,del_flag):
#        self.rrec.rtor_add = MagicMock()
#        control = control[:]
#        self.rrec.record = control[:]
#        self.rrec.rtor_update(**func_args)
#        if del_flag:
#            result = control[index]
#            del control[index]
#            self.rrec.rtor_add.assert_called_once_with(name=result.name,pos=index)
#        else:
#            self.assertEqual(self.rrec.rtor_add.called,False)
#        self.assertEqual(control,self.rrec.record)


