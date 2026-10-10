import json
import unittest
from pathlib import Path
from content import COURSES
from install import records,matches

class PackageTests(unittest.TestCase):
    def test_content_and_answers(self):
        lessons=[l for c in COURSES for ch in c['chapters'] for l in ch['lessons']]
        self.assertEqual(len(lessons),43)
        self.assertEqual(len({l['id'] for l in lessons}),43)
        self.assertEqual(sum(len(l['questions']) for l in lessons),61)
        for lesson in lessons:
            self.assertTrue(lesson['body']);self.assertTrue(lesson['instructor_notes'])
            for q in lesson['questions']:
                self.assertIn(q['answer'],range(len(q['options'])))
                self.assertEqual(len(q['options']),len(set(q['options'])))
        for c in COURSES:self.assertEqual(c['published'],0)
    def test_graph_references(self):
        specs=records(COURSES,'teacher@example.test');names={r['name'] for r in specs}
        self.assertEqual(len(names),len(specs))
        self.assertEqual(len(specs),164)
        for spec in specs:
            for field in ('course','chapter','quiz_id'):
                if field in spec:self.assertIn(spec[field],names)
            for field,childkey in [('chapters','chapter'),('lessons','lesson'),('questions','question')]:
                for child in spec.get(field,[]):self.assertIn(child[childkey],names)
        for spec in specs:
            if spec['doctype']=='LMS Course':
                self.assertEqual(spec['instructors'],[{'instructor':'teacher@example.test'}])
                self.assertEqual(spec['published'],0)
    def test_protect_teacher_changes_and_child_order(self):
        original={'body':'lesson','lessons':[{'lesson':'a'},{'lesson':'b'}]}
        self.assertTrue(matches(dict(original,modified='today'),original))
        self.assertFalse(matches(dict(original,body='teacher edit'),original))
        self.assertFalse(matches(dict(original,lessons=[{'lesson':'b'},{'lesson':'a'}]),original))
    def test_export_matches_source(self):
        exported=json.loads(Path(__file__).with_name('courses.json').read_text())
        self.assertTrue(matches(exported,COURSES))
        for c in exported:
            for ch in c['chapters']:
                for l in ch['lessons']:
                    self.assertNotIn('<script',l['html'])
                    self.assertNotIn('onerror=',l['html'])
if __name__=='__main__':unittest.main()
