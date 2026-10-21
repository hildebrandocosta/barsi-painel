import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('updater', ROOT / 'update/update.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

class AtualizacaoTest(unittest.TestCase):
    def setUp(self):
        self.a = copy.deepcopy(json.loads((ROOT/'barsi-data.json').read_text())['acoes'][0])
        self.a['cotacaoData'] = '2026-07-23'
        self.quote = {'symbol': self.a['ticker'], 'regularMarketPrice': 40,
                      'regularMarketTime': '2026-10-21T14:00:00Z'}

    def test_invalid_response_preserves_entire_reserve(self):
        for changed in [{'symbol':'OUTR3'}, {'regularMarketPrice':float('nan')},
                        {'regularMarketPrice':True}, {'regularMarketPrice':'40'},
                        {'regularMarketTime':'invalid'}, {'regularMarketTime':'2099-01-01'},
                        {'regularMarketTime':'2020-01-01'}]:
            before = copy.deepcopy(self.a)
            self.assertFalse(u.aplicar_cotacao(self.a, dict(self.quote, **changed)))
            self.assertEqual(self.a, before)

    def test_partial_fundamentals_preserve_dates_and_missing_fields(self):
        roe, margem = self.a['roe'], self.a['margem']
        payload = dict(self.quote, earningsPerShare=-2,
                       defaultKeyStatistics={'bookValue':'invalid'}, financialData={})
        self.assertTrue(u.aplicar_cotacao(self.a, payload))
        self.assertEqual(self.a['pl'], -20)
        self.assertEqual(self.a['roe'], roe)
        self.assertEqual(self.a['margem'], margem)
        self.assertIsNone(self.a['fundamentosData'])

    def test_zero_is_data(self):
        payload = dict(self.quote, earningsPerShare=0, dividendRate=0,
                       financialData={'returnOnEquity':0,'profitMargins':0})
        self.assertTrue(u.aplicar_cotacao(self.a, payload))
        self.assertIsNone(self.a['pl'])
        for field in ['roe','margem','dy','dividAnual']:
            self.assertEqual(self.a[field], 0)

    def test_list_price_has_no_fabricated_market_date(self):
        self.assertTrue(u.aplicar_lista(self.a, {'stock':self.a['ticker'],'close':41}, '2026-10-21'))
        self.assertIsNone(self.a['cotacaoData'])
        self.assertEqual(self.a['cotacaoConsulta'], '2026-10-21')

    def test_auth_rate_limit_and_offline_preserve_reserve(self):
        for exc in [HTTPError('url',401,'auth',None,None),HTTPError('url',429,'rate',None,None),TimeoutError()]:
            data = {'acoes':[copy.deepcopy(self.a)]}
            before = copy.deepcopy(data)
            with patch.object(u,'BRAPI_TOKEN','test'), patch.object(u,'consultar',side_effect=exc), patch.object(u.time,'sleep'):
                self.assertEqual(u.atualizar_fundamentos(data),0)
            self.assertEqual(data,before)

    def test_module_denied_still_accepts_basic_quote(self):
        data = {'acoes':[copy.deepcopy(self.a)]}
        responses = [HTTPError('url',403,'plan',None,None),{'results':[self.quote]}]
        with patch.object(u,'BRAPI_TOKEN','test'), patch.object(u,'consultar',side_effect=responses), patch.object(u.time,'sleep'):
            self.assertEqual(u.atualizar_fundamentos(data),1)
        self.assertEqual(data['acoes'][0]['cotacao'],40)

if __name__ == '__main__':
    unittest.main()
