"""Build review-only catalog and reproducible draft seed data; standard library only."""
import copy
import html
import json
import re
from pathlib import Path
from content import COURSES
ROOT=Path(__file__).resolve().parent

def inline(text):
    text=html.escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',text)
    text=re.sub(r'\[([^\]]+)\]\((https://[^\s)]+)\)',r'<a href="\2">\1</a>',text)
    return text

def render(body):
    output=[]; table=[]; listing=[]
    def flush():
        if table:
            output.append('<div class="table-scroll"><table>'+''.join('<tr>'+''.join('<'+('th' if i==0 else 'td')+'>'+inline(cell.strip())+'</'+('th' if i==0 else 'td')+'>' for cell in row.strip('|').split('|'))+'</tr>' for i,row in enumerate(table))+'</table></div>');table.clear()
        if listing:
            output.append('<ul>'+''.join('<li>'+inline(x)+'</li>' for x in listing)+'</ul>');listing.clear()
    for line in body.splitlines():
        line=line.strip()
        if line.startswith('|'):
            if not re.match(r'^\|[\s:|\-]+$',line):table.append(line)
            continue
        if re.match(r'^(\d+\. |[-*] )',line):
            listing.append(re.sub(r'^(\d+\. |[-*] )','',line));continue
        flush()
        if not line:continue
        if line.startswith('<div dir="rtl" lang="ar"') and line.endswith('</div>'):
            text=re.sub('<[^>]+>','',line);output.append('<p class="arabic" lang="ar" dir="rtl">'+html.escape(text)+'</p>')
        elif line.startswith('#'):
            match=re.match(r'^(#{1,6})\s+(.*)',line)
            output.append('<h3>'+inline(match[2] if match else line)+'</h3>')
        elif line.startswith('>'):output.append('<blockquote>'+inline(line.lstrip('> '))+'</blockquote>')
        elif line=='---':output.append('<hr>')
        else:output.append('<p>'+inline(line)+'</p>')
    flush();return '\n'.join(output)

def build():
    data=copy.deepcopy(COURSES)
    for c in data:
        for ch in c['chapters']:
            for l in ch['lessons']:l['html']=render(l['body'])
    (ROOT/'courses.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'catalog.js').write_text('window.ALLIM_COURSES = '+json.dumps(data,ensure_ascii=False).replace('<','\\u003c')+';\n')
    print('Built',len(data),'courses,',sum(len(ch['lessons']) for c in data for ch in c['chapters']),'lessons')
if __name__=='__main__':build()
