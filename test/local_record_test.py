import unittest
from nose_parameterized import parameterized
from mock import MagicMock
from mock import patch

from churada.record import LocalRecord
from generators import ltor_gen,rtor_gen

ltor_test = [ltor_gen(name=str(i),path='/'+str(i),size=i) for i in range(0,5)]
ltor_elem = ltor_gen(name='5',path='/5',size=5)
ltor_empty = ltor_gen(name='ltor_empty',path='/emptypath')

class LocalRecordTest(unittest.TestCase):
    def setUp(self):
        self.shell = MagicMock()
        self.lrec = LocalRecord(self.shell)
    @parameterized.expand(
       [("empty_args",ltor_test,{},{},False),
#        ("empty_object_1",ltor_test,{'ltor':ltor_gen(name='ltor_empty')},{},False),
#        ("empty_object_2",ltor_test,{'ltor':ltor_gen(path='ltor_empty')},{},False),
#        ("empty_path",ltor_test,{'path':''},{},False),
        ("duplicate_object",ltor_test,{'ltor':ltor_test[3]},{},False),
        ("duplicate_path_1",ltor_test,{'path':'/3'},{'name':'4','path':'/3'},False),
        ("duplicate_path_2",ltor_test,{'ltor':ltor_gen(name='not4',path='/4')},{},False),
        ("unique_object",ltor_test,{'ltor':ltor_elem},{'name':'5','path':'/5'},True),
        ("unique_path",ltor_test,{'path':'5'},{'name':'5','path':'/5'},True),
        ("insert",ltor_test,{'ltor':ltor_elem,'pos':2},{'name':'5','path':'/5'},True),
        ("arg_priority",ltor_test,{'ltor':ltor_elem,'path':'/6'},{'name':'5','path':'/5'},True)]
        )
    @patch('churada.record.LocalTorrent')
    @patch('time.time')
    def ltor_add_test(self,_,control,func_args,obj_args,append_flag,mock_time,mock_ltor):
        if obj_args:
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
        ("present_path",ltor_test,{'path':'/2'},ltor_test[2]),
        ("present_object",ltor_test,{'ltor':ltor_test[4]},ltor_test[4]),
        ("equal_object_1",ltor_test,{'ltor':ltor_gen(name='4',path='/not4')},ltor_test[4]),
        ("equal_object_2",ltor_test,{'ltor':ltor_gen(name='not4',path='/4')},ltor_test[4]),
        ("absent_name",ltor_test,{'name':'5'},None),
        ("absent_path",ltor_test,{'path':'/5'},None),
        ("absent_object",ltor_test,{'ltor':ltor_gen(name='5',path='/5')},None),
        ("arg_priority_1",ltor_test,{'ltor':ltor_test[3],'name':'4','path':'/2'},ltor_test[3]),
        ("arg_priority_2",ltor_test,{'ltor':ltor_test[3],'name':'4'},ltor_test[3]),
        ("arg_priority_3",ltor_test,{'ltor':ltor_test[3],'path':'/4'},ltor_test[3]),
        ("arg_priority_4",ltor_test,{'name':'3','path':'/4'},ltor_test[3])]
       )
    def ltor_find_test(self,_,control,func_args,return_val):
        self.lrec.record = control[:]
        result = self.lrec.ltor_find(**func_args)
        self.assertEqual(result,return_val)
    @parameterized.expand(
       [("empty_args",ltor_test,{},[],False),
#        ("empty_object",ltor_test,{'ltor':ltor_gen(name='ltor_empty')},[],False),
#        ("empty_path",ltor_test,{'path':''},[],False),
#        ("empty_name",ltor_test,{'name':''},[],False),
        ("present_object",ltor_test,{'ltor':ltor_elem},[3,ltor_elem],True),
        ("present_path",ltor_test,{'path':'/5'},[3,ltor_elem],True),
        ("present_name",ltor_test,{'name':'5'},[3,ltor_elem],True),
        ("absent_name",ltor_test,{'name':'6'},[],False),
        ("absent_path",ltor_test,{'path':'/6'},[],False),
        ("absent_object",ltor_test,{'ltor':ltor_elem},[],False),
        ("arg_priority_1",ltor_test,{'ltor':ltor_elem,'name':'3','path':'/2'},[3,ltor_elem],True),
        ("arg_priority_2",ltor_test,{'ltor':ltor_elem,'name':'3'},[3,ltor_elem],True),
        ("arg_priority_3",ltor_test,{'ltor':ltor_elem,'path':'/3'},[3,ltor_elem],True),
        ("arg_priority_4",ltor_test,{'name':'5','path':'/4'},[3,ltor_elem],True)]
       )
    def ltor_del_test(self,_,control,func_args,ins_args,del_flag):
        self.lrec.record = control[:]
        if del_flag:
            self.lrec.record.insert(*ins_args)
        self.lrec.ltor_del(**func_args)
        self.assertEqual(self.lrec.record,control)
#    @parameterized.expand(
#       [("empty_args",ltor_test,{},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("empty_obj",ltor_test,{'ltor':ltor_gen(name='ltor_empty')},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("empty_name",ltor_test,{'name':''},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("empty_path",ltor_test,{'path':''},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("present_obj",ltor_test,{'ltor':ltor_test[1]},{'name':'upd_name','path':'upd_path'},1,True,False),
#        ("present_name",ltor_test,{'name':'1'},{'name':'upd_name','path':'upd_path'},1,True,False),
#        ("present_path",ltor_test,{'name':'1'},{'name':'upd_name','path':'upd_path'},1,True,False),
#        ("absent_obj",ltor_test,{'ltor':ltor_elem},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("absent_name",ltor_test,{'name':'5'},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("absent_path",ltor_test,{'path':'5'},{'name':'upd_name','path':'upd_path'},1,False,False),
#        ("empty_name_update",ltor_test,{'name':'1'},{'name':'','path':'upd_path'},1,False,True),
#        ("empty_path_update",ltor_test,{'path':'1'},{'name':'upd_name','path':''},1,False,True),
#        ("arg_priority_1",ltor_test,{'ltor':ltor_test[1],'name':'2','path':'3'},{'name':'upd_name','path':'upd_path'},1,True,False),
#        ("arg_priority_2",ltor_test,{'ltor':ltor_test[1],'name':'2'},{'name':'upd_name','path':'upd_path'},1,True,False),
#        ("arg_priority_3",ltor_test,{'ltor':ltor_test[1],'path':'3'},{'name':'upd_name','path':'upd_path'},1,True,False),
#        ("arg_priority_4",ltor_test,{'name':'2','path':'3'},{'name':'upd_name','path':'upd_path'},2,True,False)]
#       )
#    @patch('churada.core.LocalTorrent')
#    def ltor_update_test(self,_,control,func_args,upd_args,index,upd_flag,del_flag,mock_ltor):
#        mock_ltor.return_value = ltor_gen(**upd_args)
#        control = deepcopy(control)
#        self.lrec.record = deepcopy(control)
#        for ltor in self.lrec.record:
#            ltor._LocalTorrent__parse.side_effect = mock_ltor_lambda(ltor,upd_args)
#        if del_flag:
#            del control[index]
#        if upd_flag:
#            mock_ltor_parse(control[index],**upd_args)
#        self.lrec.ltor_update(**func_args)
#        self.assertEquals(self.lrec.record,control)


