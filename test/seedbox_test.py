import unittest
from nose_parameterized import parameterized
from mock import MagicMock
from mock import patch

from churada.seedbox import Seedbox
from churada.rule import Rule,CompositeRule
from generators import ltor_gen,rtor_gen

ltor_test = [ltor_gen(name=str(i),path="/"+str(i),size=i) for i in range(0,5)]
ltor_elem = ltor_gen(name='5',path='/5',size=5)
ltor_empty = ltor_gen(name='ltor_empty',path='/path_empty')

rtor_test = [rtor_gen(name=str(i),state=str(i),size=i) for i in range(0,5)]
rtor_elem = rtor_gen(name='5',state='5',size=5)

down_list = [rtor_gen(name=str(i),state=str(i),size=i) for i in range(10,5,-1)]
up_list = [ltor_gen(name=str(i),path="/"+str(i),size=i) for i in range(10,5,-1)]
info_list = [rtor_elem] + [rtor_gen(name=str(i),state=str(i),size=i) for i in range(20,5,-1)]
size = 185
paths = {'remote_torrent':"remote_torrent",
         'remote_data':"remote_data",
         'local_data':"local_data"}

# download valid, download path, delete valid

rule_list = {'name_not_invalid':Rule('name',lambda x: x != 'invalid'),
             'size_lt_50':Rule('size',lambda x: x < 50),
             'state_seeding':Rule('state',lambda x: x != 'NotSeeding')
             }

valid_rule = CompositeRule([rule for key,rule in rule_list.items()],lambda x,y,z: x and y and z)

# dummy rules - could be empty entries in dict
rules = {'download_valid':[valid_rule],
        'download_path':[(valid_rule,'/high_prio',40),(valid_rule,'/low_prio',30)],
        'delete_valid':[valid_rule]}

capacity = 200
uname = 'uname'
host = 'host'

#rtor_download_valid_1 = rtor_gen(name='invalid_download_1',state='Seeding',size=60)
#rtor_download_valid_2 = rtor_gen(name='invalid_download_2',state='Seeding',size=40)
#rtor_download_valid_3 = rtor_gen(name='invalid_download_1',state='Seeding',size=40)
#rtor_download_invalid = rtor_gen(name='invalid_download_2',state='Seeding',size=60)
#rtor_rule_path = rtor_gen(name='download_to_rule_path',state='Seeding',size=50)
#rtor_delete_invalid = rtor_gen(name='do_not_delete',state='Seeding',size=50)


# note that validity/path rules are not tested
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
         ("nodelete_delete",info_list,{'space':5,'rtor':rtor_elem,'rtor_iter':iter(info_list),'exitcode':1,'output':None},True)
#         ("invalid_delete",[rtor_delete_invalid]+info_list,{'space':60,'rtor':rtor_elem,'rtor_iter':iter([rtor_delete_invalid]+info_list),'exitcode':0,'output':None},False)
         ])
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
        ("nodownload_download",down_list,down_list[3],{'space':7,'rtor':rtor_elem,'rtor_iter':iter(down_list),'exitcode':1,'output':None},True)
#        ("nodownload_valid",
        ])
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

