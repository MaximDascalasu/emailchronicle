"""Deterministic, explainable search without models or external services."""
import difflib
import re
import shlex
from itertools import islice

MAX_MATCHES_PER_TERM = 128
MAX_HIGHLIGHTS = 500

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
        row=dict(source);matches=[];score=0;limited=False
        for requested, alternatives in query_plan:
            found=[]
            for actual, reason, group in alternatives:
                for field in FIELDS:
                    text=row.get(field) or ''
                    for hit in islice(pattern(actual).finditer(text), MAX_MATCHES_PER_TERM-len(found)):
                        found.append({'query':requested,'matched':hit[0],'field':field,'reason':reason,
                                      'group':group,'start':hit.start(),'end':hit.end()})
                    if len(found) >= MAX_MATCHES_PER_TERM:
                        limited=True
                        break
                if len(found) >= MAX_MATCHES_PER_TERM:
                    break
            if not found and mode=='approximate' and requested.isalpha() and len(requested)>=5:
                for field in FIELDS:
                    for hit in re.finditer(r'\w+',row.get(field) or ''):
                        word=hit[0]
                        if abs(len(word)-len(requested))<=1 and difflib.SequenceMatcher(None,requested.casefold(),word.casefold()).ratio()>=0.84:
                            found.append({'query':requested,'matched':word,'field':field,'reason':'approximate',
                                          'group':None,'start':hit.start(),'end':hit.end()})
                            if len(found) >= MAX_MATCHES_PER_TERM:
                                limited=True
                                break
                    if len(found) >= MAX_MATCHES_PER_TERM:
                        break
            if not found:
                break
            score += max({'exact':100,'synonym':60,'approximate':25}[f['reason']] for f in found)
            matches.extend(found)
        else:
            row['search_matches']=matches;row['search_score']=score
            row['search_matches_limited']=limited
            output.append(row)
    # Stable ties preserve chronology; relevance is opt-in.
    if relevance:output.sort(key=lambda row:-row['search_score'])
    return output


def highlight_ranges(text, matched_terms, limit=MAX_HIGHLIGHTS):
    """Return bounded UTF-16 highlight ranges with a single prefix traversal.

    Original evidence and search membership are unchanged by display limits.
    """
    hits=[]
    for term in dict.fromkeys(matched_terms):
        hits.extend((m.start(),m.end()) for m in islice(pattern(term).finditer(text),limit-len(hits)))
        if len(hits)>=limit:
            break
    positions=iter(sorted({p for hit in hits for p in hit}))
    target=next(positions,None)
    offsets={}
    units=0
    for index,char in enumerate(text):
        if index==target:
            offsets[index]=units
            target=next(positions,None)
            if target is None:
                break
        units+=2 if ord(char)>0xffff else 1
    if target==len(text):
        offsets[target]=units
    return [(offsets[start],offsets[end]) for start,end in hits]
