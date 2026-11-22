import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class ConfigureTrialTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.db = Mock()
        self.frappe.db.get_value.return_value = 1
        self.frappe.has_permission = Mock(return_value=True)
        self.frappe.throw = Mock(side_effect=ValueError)
        self.config = types.SimpleNamespace(coordinator=None,response_hours=24,email_enabled=0,save=Mock())
        self.frappe.get_single = Mock(return_value=self.config)
        self.frappe.get_all = Mock(return_value=[])
        self.utils = types.SimpleNamespace(cint=lambda x:int(x or 0),add_to_date=lambda date,**kw:'due-after-24h')
        self.lifecycle = types.SimpleNamespace(REQUEST='ALLIM Trial Lesson Request',SETTINGS='ALLIM Trial Settings')
        self.modules = patch.dict(sys.modules,{'frappe':self.frappe,'frappe.utils':self.utils,'allimquran.trial_lifecycle':self.lifecycle})
        self.modules.start();self.addCleanup(self.modules.stop)
        spec=importlib.util.spec_from_file_location('trial_setup_test',Path('allimquran/trial_setup.py'))
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)

    def test_disabled_account_rejected_before_writes(self):
        self.frappe.db.get_value.return_value=0
        with self.assertRaises(ValueError):self.module.configure('owner@example.test')
        self.frappe.get_single.assert_not_called()

    def test_missing_permission_rejected_before_writes(self):
        self.frappe.has_permission.return_value=False
        with self.assertRaises(ValueError):self.module.configure('owner@example.test')
        self.frappe.get_single.assert_not_called()

    def test_invalid_deadline_rejected_before_writes(self):
        for hours in [0,-1,169]:
            with self.assertRaises(ValueError):self.module.configure('owner@example.test',hours)
        self.frappe.get_single.assert_not_called()

    def test_configure_does_not_enable_learner_mail_or_reassign_records_by_default(self):
        self.module.configure('owner@example.test')
        self.assertEqual(self.config.coordinator,'owner@example.test')
        self.assertEqual(self.config.email_enabled,0)
        self.frappe.get_all.assert_not_called()

    def test_backfill_preserves_existing_assignments_and_closed_records(self):
        docs={
            'open':types.SimpleNamespace(status='New',trial_coordinator=None,trial_follow_up=None,creation='created',consent=0,save=Mock()),
            'assigned':types.SimpleNamespace(status='New',trial_coordinator='other@example.test',save=Mock()),
            'closed':types.SimpleNamespace(status='Closed',trial_coordinator=None,save=Mock()),
        }
        self.frappe.get_all.return_value=list(docs)
        self.frappe.get_doc=Mock(side_effect=lambda dt,name,**kw:docs[name])
        result=self.module.configure('owner@example.test',assign_existing=True)
        self.assertEqual(result['assigned_existing'],['open'])
        self.assertEqual(docs['open'].trial_follow_up,'due-after-24h')
        self.assertEqual(docs['open'].consent,0)
        docs['assigned'].save.assert_not_called();docs['closed'].save.assert_not_called()
        again=self.module.configure('owner@example.test',assign_existing=True)
        self.assertEqual(again['assigned_existing'],[])
        docs['open'].save.assert_called_once()

    def test_existing_follow_up_is_preserved(self):
        doc=types.SimpleNamespace(status='Contacted',trial_coordinator=None,trial_follow_up='agreed-deadline',creation='created',save=Mock())
        self.frappe.get_all.return_value=['open'];self.frappe.get_doc=Mock(return_value=doc)
        self.module.configure('owner@example.test',assign_existing=True)
        self.assertEqual(doc.trial_follow_up,'agreed-deadline')


if __name__=='__main__':unittest.main()
