"""Deterministic, explainable search without models or external services."""
import difflib
import re
import shlex

FIELDS = ('subject', 'body', 'sender', 'recipients', 'message_id')


def terms(query):
    try:
        lexer = shlex.shlex(query, posix=True)
        lexer.quotes = '"'
        lexer.escape = ''
        lexer.commenters = ''
        lexer.whitespace_split = True
        result = list(dict.fromkeys(t.strip() for t in lexer if t.strip()))
    except ValueError as exc:
        raise ValueError('Close quoted phrases before searching.') from exc
    if len(result) > 20 or len(query) > 1000:
        raise ValueError('Use at most 20 search terms and 1000 characters.')
    return result


def pattern(term):
    return re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)', re.IGNORECASE)


def plan(query, mode, groups):
    if mode not in ('exact', 'expanded', 'approximate'):
        raise ValueError('Unknown search mode')
    result=[]
    for term in terms(query):
        alternatives=[(term, 'exact', None)]
        if mode != 'exact':
            for group in groups:
                if group.get('enabled') and any(term.casefold()==t.casefold() for t in group['terms']):
                    alternatives.extend((t,'synonym',group['name']) for t in group['terms'] if t.casefold()!=term.casefold())
        result.append((term, alternatives))
    return result


def search(rows, query, mode='exact', groups=(), relevance=False):
    query_plan=plan(query,mode,groups)
    output=[]
    for source in rows:
        row=dict(source);matches=[];score=0
        for requested, alternatives in query_plan:
            found=[]
            for actual, reason, group in alternatives:
                for field in FIELDS:
                    text=row.get(field) or ''
                    for hit in pattern(actual).finditer(text):
                        found.append({'query':requested,'matched':hit[0],'field':field,'reason':reason,
                                      'group':group,'start':hit.start(),'end':hit.end()})
            if not found and mode=='approximate' and requested.isalpha() and len(requested)>=5:
                for field in FIELDS:
                    for hit in re.finditer(r'\w+',row.get(field) or ''):
                        word=hit[0]
                        if abs(len(word)-len(requested))<=1 and difflib.SequenceMatcher(None,requested.casefold(),word.casefold()).ratio()>=0.84:
                            found.append({'query':requested,'matched':word,'field':field,'reason':'approximate',
                                          'group':None,'start':hit.start(),'end':hit.end()})
            if not found:
                break
            score += max({'exact':100,'synonym':60,'approximate':25}[f['reason']] for f in found)
            matches.extend(found)
        else:
            row['search_matches']=matches;row['search_score']=score
            output.append(row)
    # Stable ties preserve chronology; relevance is opt-in.
    if relevance:output.sort(key=lambda row:-row['search_score'])
    return output
