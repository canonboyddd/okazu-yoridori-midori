import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import qa_production as qa

class LinkContractTests(unittest.TestCase):
    def test_valid_contract_never_sends_click(self):
        with patch.object(qa,'fetch',side_effect=AssertionError('network forbidden')):
            qa.validate_fanza_link('https://al.dmm.co.jp/?af_id=okazumidori-990&ch=api&lurl=https%3A%2F%2Fwww.dmm.co.jp%2Fdigital%2Fvideoa%2F')
    def test_invalid_host_id_channel_and_destination_are_rejected(self):
        for url in ['https://al.dmm.co.jp.evil.test/?af_id=okazumidori-990&ch=api&lurl=https://www.dmm.co.jp/','https://al.dmm.co.jp/?af_id=wrong&ch=api&lurl=https://www.dmm.co.jp/','https://al.dmm.co.jp/?af_id=okazumidori-001&ch=link_tool&lurl=https://www.dmm.co.jp/','https://al.dmm.co.jp/?af_id=okazumidori-990&ch=api&lurl=javascript:alert(1)']:
            with self.subTest(url=url),self.assertRaises(RuntimeError):qa.validate_fanza_link(url)

if __name__=='__main__':unittest.main()
