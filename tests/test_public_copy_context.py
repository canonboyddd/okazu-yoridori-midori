import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import remove_internal_operator_copy as audit

class PrivacyContextTests(unittest.TestCase):
    def test_actual_processor_can_be_named_only_on_the_two_privacy_routes(self):
        text='<html><p>匿名の利用状況集計にはCloudflareを利用します。</p></html>'
        for path in ['privacy','privacy.html']:
            self.assertEqual(audit.remaining_audit_terms(text,audit.ROOT/path),[])
        for path in ['index.html','sale/index.html','articles/privacy.html']:
            self.assertIn('Cloudflare',audit.remaining_audit_terms(text,audit.ROOT/path))
    def test_other_developer_copy_is_still_rejected_on_privacy_pages(self):
        for path in ['privacy','privacy.html']:
            terms=audit.remaining_audit_terms('<html>Cloudflare GitHub デプロイ</html>',audit.ROOT/path)
            self.assertEqual(terms,['GitHub','デプロイ'])

if __name__=='__main__':unittest.main()
