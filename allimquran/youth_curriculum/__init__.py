"""Create-only draft course seed. Run explicitly after matching the deployment manifest."""
from pathlib import Path
import json
from html import escape


def records(courses, instructor):
    result=[]
    for c in courses:
        course='allim-y1-'+c['id'].removeprefix('allim-')
        chapters=[]
        for ch in c['chapters']:
            chapter=course+'-'+ch['id']; lessons=[]
            for l in ch['lessons']:
                name='allim-y1-'+l['id']; quiz=name+'-quiz'; questions=[]
                for i,q in enumerate(l['questions']):
                    qname=name+'-q'+str(i+1)
                    fields=dict(type='Choices',question='<p>'+escape(q['prompt'])+'</p>',multiple=0)
                    for n,option in enumerate(q['options'],1):
                        fields['option_'+str(n)]=escape(option)
                        fields['is_correct_'+str(n)]=int(n-1==q['answer'])
                        fields['explanation_'+str(n)]=escape(q['explanation'])
                    result.append(dict(doctype='LMS Question',name=qname,**fields))
                    questions.append(dict(question=qname,marks=1,type="Choices",question_detail=fields["question"]))
                result.append(dict(doctype='LMS Quiz',name=quiz,title=l['title']+' · проверка',course=course,questions=questions,
                    passing_percentage=100,total_marks=len(questions),show_answers=1,show_submission_history=1,max_attempts=0,enable_proctoring=0))
                body=l['body']+'\n\n## Короткая практика\n'+l['kids']+'\n\n## Дополнительный шаг для подростков\n'+l['teens']
                if l.get('reference'):
                    ref=l['reference'];body+='\n\n[Открыть практику в ALLIM](https://allimquran.com/learn?view=read&lang=ru&surah='+str(ref['surah'])+'&ayah='+str(ref['ayah'])+')'
                result.append(dict(doctype='Course Lesson',name=name,title=l['title'],course=course,chapter=chapter,body=body,
                    instructor_notes=l['instructor_notes'],quiz_id=quiz,include_in_preview=0))
                lessons.append(dict(lesson=name))
            result.append(dict(doctype='Course Chapter',name=chapter,title=ch['title'],course=course,lessons=lessons))
            chapters.append(dict(chapter=chapter))
        result.append(dict(doctype='LMS Course',name=course,title=c['title'],short_introduction=c['short_introduction'],description=c['description'],
            tags=c['marker']+', ALLIM-YOUTH-V1, ru',instructors=[dict(instructor=instructor)],chapters=chapters,
            published=0,paid_course=0,enable_certification=0,enforce_lesson_completion=1))
    return result


def matches(actual, expected):
    """Compare managed fields, including child order; ignore system/computed fields."""
    if isinstance(expected,dict):
        return isinstance(actual,dict) and all(matches(actual.get(k),v) for k,v in expected.items())
    if isinstance(expected,list):
        return isinstance(actual,list) and len(actual)==len(expected) and all(matches(a,b) for a,b in zip(actual,expected))
    if expected == 0 and actual in (None,''): return True
    return actual==expected


def execute(instructor, apply=False):
    import frappe
    from frappe.utils import cint
    apply=bool(cint(apply))
    if not instructor or not frappe.db.exists('User',instructor):
        frappe.throw('Specify an existing enabled test instructor.')
    user=frappe.get_doc('User',instructor)
    if not user.enabled or not set(frappe.get_roles(instructor)) & {'Course Creator','Moderator'}:
        frappe.throw('Instructor must be enabled and have an authoring role.')
    courses=json.loads((Path(__file__).parent/'courses.json').read_text())
    specs=records(courses,instructor)
    # Catch legacy course drafts rather than silently creating a second alphabet course.
    names={r['name'] for r in specs if r['doctype']=='LMS Course'}
    for c in courses:
        collisions=frappe.get_all('LMS Course',filters={'title':c['title']},pluck='name')
        if any(name not in names for name in collisions):
            frappe.throw('An existing course has this title. Review its migration before seeding: '+c['title'])
    legacy=frappe.get_all('LMS Course',filters={'tags':['like','%ALLIM-C01%']},pluck='name')
    if any(name not in names for name in legacy):frappe.throw('Legacy ALLIM-C01 draft found; resolve migration explicitly.')
    existing=[]; missing=[]
    for spec in specs:
        meta=frappe.get_meta(spec['doctype'])
        for field in spec:
            if field not in ('name','doctype') and not meta.has_field(field):
                frappe.throw('Installed schema differs: '+spec['doctype']+'.'+field)
        if frappe.db.exists(spec['doctype'],spec['name']):
            doc=frappe.get_doc(spec['doctype'],spec['name']);doc.check_permission('read')
            if spec['doctype']=='LMS Course' and doc.published:
                frappe.throw('Published course is protected: '+doc.name)
            if not matches(doc.as_dict(),spec):frappe.throw('Existing content differs; no overwrite allowed: '+doc.name)
            existing.append(spec['name'])
        else:
            if not frappe.has_permission(spec['doctype'],'create'):frappe.throw('Missing create permission: '+spec['doctype'])
            missing.append(spec)
    # Incomplete seed state is not repaired automatically: it may contain teacher edits.
    if existing and missing:frappe.throw('Partial seed detected. Review before creating additional records.')
    report=dict(dry_run=not apply,existing=len(existing),create=len(missing),courses=3,published=False)
    if not apply or not missing:return report
    frappe.db.savepoint('allim_youth_seed')
    try:
        def insert(spec,omitted=()):
            data={k:v for k,v in spec.items() if k not in omitted}
            return frappe.get_doc(data).insert(set_name=spec["name"])
        for dt,omitted in [('LMS Course',('chapters',)),('Course Chapter',('lessons',)),('LMS Question',()),('LMS Quiz',()),('Course Lesson',())]:
            for spec in missing:
                if spec['doctype']==dt:insert(spec,omitted)
        for dt,field in [('Course Chapter','lessons'),('LMS Course','chapters')]:
            for spec in missing:
                if spec['doctype']==dt:
                    doc=frappe.get_doc(dt,spec['name']);doc.set(field,spec[field]);doc.save()
        for spec in missing:
            if not matches(frappe.get_doc(spec['doctype'],spec['name']).as_dict(),spec):
                frappe.throw('Read-back differs; rolled back: '+spec['name'])
    except Exception:
        frappe.db.rollback(save_point='allim_youth_seed');raise
    # Commit is owned by the invoking command/transaction, not this helper.
    return report
