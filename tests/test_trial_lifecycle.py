import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from allimquran.trial_rules import check, secure_url

NOW = datetime(2026, 11, 22, 12)


class RulesTest(unittest.TestCase):
    def test_website_controller_matches_route_loader_convention(self):
        self.assertTrue(Path('allimquran/www/my_trial_lesson.py').is_file())


    def schedule(self):
        return dict(status='Scheduled',trial_coordinator='coordinator@example.test',trial_teacher='teacher@example.test',
                    trial_start=str(NOW+timedelta(days=1)),trial_timezone='Europe/Moscow',trial_duration=30,
                    trial_meeting_url='https://example.test/lesson')

    def result(self):
        return dict(self.schedule(),status='Completed',trial_start=str(NOW-timedelta(hours=1)),
                    trial_completed_at=str(NOW),trial_result='Read a short passage',trial_recommendation='Reading practice',
                    trial_next_step='Choose a weekly time',trial_follow_up=str(NOW+timedelta(days=1)))

    def test_new_requires_real_consent(self):
        self.assertIn('Consent',check({'status':'New','consent':0},None,NOW))
        self.assertIsNone(check({'status':'New','consent':1},None,NOW))

    def test_cannot_create_fabricated_completed_lesson(self):
        self.assertIsNotNone(check(self.result(),None,NOW))

    def test_schedule_requires_actual_appointment(self):
        self.assertIsNone(check(self.schedule(),{'status':'New'},NOW))
        for field in ['trial_start','trial_teacher','trial_meeting_url','trial_timezone','trial_duration']:
            data=self.schedule(); data[field]=''
            self.assertIsNotNone(check(data,{'status':'New'},NOW),field)

    def test_schedule_requires_owner_and_future_time(self):
        data=self.schedule();data['trial_coordinator']=''
        self.assertIn('coordinator',check(data,{'status':'New'},NOW))
        data=self.schedule();data['trial_start']=str(NOW)
        self.assertIn('future',check(data,{'status':'New'},NOW))

    def test_meeting_links_cannot_execute_code_or_embed_credentials(self):
        for url in ['javascript:alert(1)','http://example.test','https://user:pass@example.test','//example.test','https://example.test/\n']:
            self.assertFalse(secure_url(url),url)
        self.assertTrue(secure_url('https://example.test/room?id=123'))

    def test_completion_requires_all_result_fields(self):
        old=dict(self.schedule(),trial_start=str(NOW-timedelta(hours=1)))
        self.assertIsNone(check(self.result(),old,NOW))
        for field in ['trial_result','trial_recommendation','trial_next_step','trial_completed_at','trial_teacher']:
            data=self.result();data[field]=''
            self.assertIsNotNone(check(data,old,NOW),field)

    def test_future_and_prelesson_results_rejected(self):
        old=dict(self.schedule(),trial_start=str(NOW-timedelta(hours=1)))
        for at in [NOW+timedelta(hours=1),NOW-timedelta(hours=2)]:
            self.assertIsNotNone(check(dict(self.result(),trial_completed_at=str(at)),old,NOW))

    def test_no_show_requires_past_start_reason_and_next_action(self):
        data=dict(self.schedule(),status='No Show',trial_reason='Did not join',trial_follow_up=str(NOW+timedelta(days=1)))
        self.assertIsNotNone(check(data,self.schedule(),NOW))
        data['trial_start']=str(NOW-timedelta(hours=1))
        self.assertIsNone(check(data,self.schedule(),NOW))
        data['trial_follow_up']=''
        self.assertIsNotNone(check(data,self.schedule(),NOW))

    def test_enrollment_is_not_a_synonym_for_trial(self):
        self.assertIsNotNone(check(dict(self.result(),status='Enrolled'),self.schedule(),NOW,True))
        self.assertIsNotNone(check(dict(self.result(),status='Enrolled'),self.result(),NOW,False))
        self.assertIsNone(check(dict(self.result(),status='Enrolled'),self.result(),NOW,True))

    def test_closed_cannot_silently_reopen(self):
        self.assertIsNotNone(check(self.schedule(),{'status':'Closed'},NOW))

    def test_legacy_untouched_status_can_be_edited(self):
        row={'status':'Scheduled','full_name':'Test'}
        self.assertIsNone(check(row,dict(row),NOW))


class Row(dict):
    def __getattr__(self,key): return self.get(key)
    def db_set(self,key,value,**kw): self[key]=value


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.frappe=types.ModuleType('frappe')
        self.frappe.whitelist=lambda **kw: lambda fn: fn
        self.frappe._=lambda x:x
        self.frappe.db=Mock()
        self.frappe.db.get_value.return_value=True
        self.frappe.db.exists.return_value=False
        self.frappe.sendmail=Mock()
        self.frappe.session=Row(user='learner@example.test')
        self.frappe.throw=Mock(side_effect=PermissionError)
        self.frappe.PermissionError=PermissionError
        util=types.ModuleType('frappe.utils')
        for name in ['add_to_date','cint','get_datetime','get_system_timezone','get_url','now_datetime']:
            setattr(util,name,Mock())
        util.cint=lambda x:int(x or 0)
        util.get_datetime=lambda x:datetime.fromisoformat(str(x))
        util.now_datetime=lambda:NOW
        util.get_system_timezone=lambda:'UTC'
        util.get_url=lambda x:'https://example.test'+x
        spec=importlib.util.spec_from_file_location('trial_under_test',Path('allimquran/trial_lifecycle.py'))
        self.module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'frappe':self.frappe,'frappe.utils':util}):spec.loader.exec_module(self.module)
        self.module.settings=lambda:Row(email_enabled=1)
        self.module.message=lambda *args:('Trial','Safe body')
        self.doc=Row(name='TRIAL-TEST',trial_version=2,status='Scheduled',email='learner@example.test',consent=1,
                     trial_teacher='teacher@example.test',trial_start=str(NOW+timedelta(hours=2)))
        self.notice=Row(state='Pending',version=2,audience='Learner',recipient=self.doc.email,kind='Scheduled')
        self.frappe.get_doc=Mock(side_effect=lambda dt,*args,**kw:self.doc if dt==self.module.REQUEST else self.notice)

    def test_delivery_retries_do_not_duplicate_queued_mail(self):
        self.module.deliver('test');self.module.deliver('test')
        self.frappe.sendmail.assert_called_once()
        self.assertEqual(self.notice.state,'Queued')

    def test_changed_schedule_supersedes_old_notice(self):
        self.notice.version=1;self.module.deliver('test')
        self.assertEqual(self.notice.state,'Superseded');self.frappe.sendmail.assert_not_called()

    def test_withdrawn_consent_suppresses_mail(self):
        self.doc.consent=0;self.module.deliver('test')
        self.assertEqual(self.notice.state,'Suppressed');self.frappe.sendmail.assert_not_called()

    def test_changed_email_suppresses_old_address(self):
        self.doc.email='new@example.test';self.module.deliver('test')
        self.frappe.sendmail.assert_not_called()

    def test_disabled_outgoing_keeps_pending(self):
        self.module.settings=lambda:Row(email_enabled=0);self.module.deliver('test')
        self.assertEqual(self.notice.state,'Pending');self.frappe.sendmail.assert_not_called()

    def test_expired_reminder_suppressed(self):
        self.notice.kind='Reminder';self.doc.trial_start=str(NOW-timedelta(hours=1));self.module.deliver('test')
        self.assertEqual(self.notice.state,'Superseded');self.frappe.sendmail.assert_not_called()

    def test_canceled_reminder_suppressed(self):
        self.notice.kind='Reminder';self.doc.status='Closed';self.module.deliver('test')
        self.frappe.sendmail.assert_not_called()

    def test_inactive_teacher_suppressed(self):
        self.notice.audience='Teacher';self.frappe.db.get_value.return_value=False;self.module.deliver('test')
        self.frappe.sendmail.assert_not_called()

    def test_mail_failure_does_not_claim_queued(self):
        self.frappe.sendmail.side_effect=RuntimeError('mail unavailable')
        with self.assertRaises(RuntimeError):self.module.deliver('test')
        self.assertEqual(self.notice.state,'Pending')

    def test_existing_notice_is_idempotent(self):
        self.frappe.db.exists.return_value=True
        self.module.enqueue_notice(self.doc,'Scheduled','Learner',self.doc.email)
        self.frappe.get_doc.assert_not_called()

    def test_notice_uses_deterministic_database_name(self):
        created=Mock();self.frappe.get_doc=Mock(return_value=created)
        self.module.enqueue_notice(self.doc,'Scheduled','Learner',self.doc.email)
        key=created.insert.call_args.kwargs['set_name']
        self.assertEqual(len(key),64)
        self.assertEqual(key,self.frappe.get_doc.call_args.args[0]['name'])

    def test_learner_email_escapes_entered_results(self):
        self.doc.update(status='Completed',language='ru',trial_result='<script>alert(1)</script>',
                        trial_recommendation='A & B',trial_next_step='Read',trial_learner='learner@example.test')
        # Recover the real renderer; delivery tests otherwise stub message formatting.
        source=Path('allimquran/trial_lifecycle.py').read_text()
        import ast
        tree=ast.parse(source)
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='message')
        exec(compile(ast.Module(body=[function],type_ignores=[]),'message','exec'),self.module.__dict__)
        title,body=self.module.message(self.doc,self.notice)
        self.assertNotIn('<script>',body)
        self.assertIn('&lt;script&gt;',body)

    def test_guest_cannot_read_trial_rows(self):
        self.frappe.session.user='Guest'
        with patch.dict(sys.modules,{'allimquran.review_portal':types.SimpleNamespace(private_headers=lambda:None)}):
            with self.assertRaises(PermissionError):self.module.my_trials()

    def test_portal_scope_comes_from_session_and_hides_internal_fields(self):
        self.frappe.get_all=Mock(return_value=[Row(status='New',trial_reason='internal',trial_result='draft',trial_teacher='teacher@example.test')])
        with patch.dict(sys.modules,{'allimquran.review_portal':types.SimpleNamespace(private_headers=lambda:None)}):
            rows=self.module.my_trials()
        self.assertEqual(self.frappe.get_all.call_args.kwargs['filters'],{'trial_learner':'learner@example.test'})
        self.assertNotIn('trial_reason',rows[0]);self.assertNotIn('trial_teacher',rows[0])
        self.assertEqual(rows[0]['trial_result'],'');self.assertEqual(rows[0]['trial_meeting_url'],'')


if __name__=='__main__':unittest.main()
