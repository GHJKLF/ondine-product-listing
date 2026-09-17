import copy
import json
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('category_gate', Path(__file__).resolve().parents[1]/'scripts/verify_category_readback.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CategoryReadbackTests(unittest.TestCase):
    def setUp(self):
        self.expected = dict(shop_id='shop', product_id='product', category_id='dresses', product_updated_at='revision', source_inventory_reviewed=True, fields=[dict(key='color-pattern', type='list.metaobject_reference', values=['navy'], display_values={'navy':'Navy'}, source_evidence='source/front.jpg')])
        self.actual = {'data': {'shop': {'id':'shop'}, 'product': {'id':'product','status':'DRAFT','updatedAt':'revision','category':{'id':'dresses'},'metafields':{'nodes':[{'namespace':'shopify','key':'color-pattern','type':'list.metaobject_reference','value':'["navy"]','references':{'nodes':[{'id':'navy','displayName':'Navy'}],'pageInfo':{'hasNextPage':False}}}], 'pageInfo':{'hasNextPage':False}}}}}
    def test_complete_readback_passes(self):
        self.assertTrue(m.verify(self.expected,self.actual)['sheet_draft_allowed'])
    def test_category_only_valeria_regression(self):
        self.actual['data']['product']['metafields']['nodes']=[]
        result=m.verify(self.expected,self.actual)
        self.assertFalse(result['completion_allowed'])
        self.assertFalse(result['sheet_draft_allowed'])
    def test_fail_closed(self):
        for path,value in [('category',None),('updatedAt','old'),('id','other'),('status','ACTIVE')]:
            actual=copy.deepcopy(self.actual);actual['data']['product'][path]=value
            self.assertFalse(m.verify(self.expected,actual)['ok'],path)
        for expected in [{},dict(self.expected,fields=[]),dict(self.expected,source_inventory_reviewed=False)]:
            self.assertFalse(m.verify(expected,self.actual)['ok'])
    def test_incomplete_or_wrong_values_fail(self):
        for mutate in [lambda c:c['pageInfo'].update(hasNextPage=True),lambda c:c['nodes'][0].update(value='["brown"]'),lambda c:c['nodes'][0]['references']['nodes'][0].update(displayName='Brown'),lambda c:c['nodes'][0]['references']['pageInfo'].update(hasNextPage=True)]:
            actual=copy.deepcopy(self.actual);mutate(actual['data']['product']['metafields'])
            self.assertFalse(m.verify(self.expected,actual)['ok'])

    def test_valeria_all_ten_source_supported_fields_required(self):
        # Reported repaired display values, synthetic IDs; not a live Shopify fixture.
        inventory={'color-pattern':['Navy','Brown','Burgundy','Grey'],'size':['S','M','L','XL','2XL','3XL'],'sleeve-length-type':['Long'],'target-gender':['Female'],'care-instructions':['Hand wash','Ironing instructions'],'dress-occasion':['Casual'],'neckline':['Round'],'hemline-style':['Straight'],'age-group':['Adults'],'skirt-dress-length-type':['Maxi']}
        self.expected['fields']=[];nodes=[]
        for key,labels in inventory.items():
            refs={key+str(i):label for i,label in enumerate(labels)}
            self.expected['fields'].append(dict(key=key,type='list.metaobject_reference',values=list(refs),display_values=refs,source_evidence='Reported Valeria source evidence'))
            nodes.append(dict(namespace='shopify',key=key,type='list.metaobject_reference',value=json.dumps(list(refs)),references=dict(nodes=[dict(id=k,displayName=v) for k,v in refs.items()],pageInfo=dict(hasNextPage=False))))
        self.actual['data']['product']['metafields']['nodes']=nodes
        self.assertTrue(m.verify(self.expected,self.actual)['ok'])
        for i in range(len(nodes)):
            actual=copy.deepcopy(self.actual)
            actual['data']['product']['metafields']['nodes'].pop(i)
            self.assertFalse(m.verify(self.expected,actual)['sheet_draft_allowed'],nodes[i]['key'])
