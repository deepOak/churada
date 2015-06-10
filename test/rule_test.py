import unittest
from nose_parameterized import parameterized
from mock import MagicMock

from generators import ltor_gen,rtor_gen
from churada.rule import Rule,CompositeRule

rtor_test = [rtor_gen(name=str(i),state=2*str(i),size=i) for i in range(0,10)]
ltor_test = [ltor_gen(name=str(i),path=2*str(i),size=i) for i in range(0,10)]
class RuleTest(unittest.TestCase):
    @parameterized.expand([
        ("query_true_0",rtor_test[0],{'key':'name','func':lambda x: x == '0'},True),
        ("query_true_1",rtor_test[1],{'key':'name','func':lambda x: int(x) == 1},True),
        ("query_true_2",rtor_test[2],{'key':'size','func':lambda x: x == 2},True),
        ("query_true_3",rtor_test[3],{'key':'state','func':lambda x: x == '33'},True),
        ("query_true_4",ltor_test[0],{'key':'name','func':lambda x: int(x) == 0},True),
        ("query_true_5",ltor_test[1],{'key':'path','func':lambda x: x == '11'},True),
        ("query_false_0",rtor_test[4],{'key':'size','func':lambda x: x < 2},False),
        ("query_false_1",ltor_test[2],{'key':'size','func':lambda x: x < 2},False),
        ("query_false_2",ltor_test[3],{'key':'state','func':lambda: True},False)
        ])
    def query_test(self,_,obj,func_args,query_flag):
        rule = Rule(**func_args)
        result = rule.query(obj)
        self.assertEqual(result,query_flag)

rules = {'name_not_3':Rule('name',lambda x: str(x) != '3'),
         'name_is_3':Rule('name',lambda x: str(x) == '3'),
         'size_gt_2':Rule('size',lambda x: int(x) > 2),
         'size_eq_2':Rule('size',lambda x: int(x) == 2),
         'size_lt_2':Rule('size',lambda x: int(x) < 2),
         'state_not_4':Rule('state',lambda x: str(x) != '4'),
         'state_is_4':Rule('state',lambda x: str(x) == '4'),
         'path_is_11':Rule('path',lambda x: str(x) == '11'),
         'path_not_11':Rule('path',lambda x: str(x) != '11')
        }

class CompositeRuleTest(unittest.TestCase):
    @parameterized.expand([
        ("crule_query_1",rtor_test[0],{'rules':(rules['name_not_3'],rules['size_gt_2']),
            'crule':(lambda x,y: x and not y)},True),
        ("crule_query_2",rtor_test[0],{'rules':(rules['name_not_3'],rules['size_gt_2']),
            'crule':(lambda x,y: x or y)},True),
        ("crule_query_3",rtor_test[0],{'rules':(rules['name_not_3'],rules['size_gt_2']),
            'crule':(lambda x,y: x and y)},False)
       ])
    def query_test(self,_,obj,func_args,query_flag):
        crule = CompositeRule(**func_args)
        result = crule.query(obj)
        self.assertEqual(result,query_flag)
