"""Find and remove generation traces from a finished text / Markdown / docx / PDF file (korean-writing skill, section 10).

  python clean_traces.py FILE            report only (nothing is changed)
  python clean_traces.py FILE --fix      write FILE's cleaned copy next to it as "<name> (정리).<ext>"
      [--author 최성철]                    author for docx/PDF metadata (default 최성철)
      [--keep-dashes]                      keep em dashes (default: report them, replace only with --fix-dashes)
      [--fix-dashes]                       replace " — " / "—" with ", " (check the sentences afterwards)

What it looks at
  text   invisible characters (zero-width, BOM, soft hyphen, word joiner, bidi marks), NBSP / narrow NBSP / thin spaces,
         tool footers and trailers ("Generated with Claude", "Co-Authored-By: Claude", "as an AI", "🤖"), leftover Markdown
         (**, ##, ``` ), draft markers (⟦ ⟧, 【 】, [[결과 대기]]), em dashes.
  docx   the same in word/*.xml text, plus docProps/core.xml (creator, lastModifiedBy, description, keywords, dates, revision),
         docProps/app.xml (template statistics), docProps/custom.xml, comment / revision authors.
  pdf    document information (Author, Creator, Producer, Title, Subject, Keywords) and XMP; text is only reported.
It never removes an AI-use disclosure sentence (e.g. "생성형 AI인 Claude(Anthropic)를 사용하였으며"); it lists it so the
author can decide under the venue's policy.
"""
import re, sys, os, shutil, zipfile, tempfile, datetime

INVIS = {0x200B: 'ZERO WIDTH SPACE', 0x200C: 'ZWNJ', 0x200D: 'ZWJ', 0x2060: 'WORD JOINER', 0xFEFF: 'BOM/ZWNBSP',
         0x00AD: 'SOFT HYPHEN', 0x200E: 'LRM', 0x200F: 'RLM', 0x202A: 'LRE', 0x202B: 'RLE', 0x202C: 'PDF', 0x202D: 'LRO',
         0x202E: 'RLO', 0x2066: 'LRI', 0x2067: 'RLI', 0x2068: 'FSI', 0x2069: 'PDI', 0x180E: 'MONGOLIAN VS',
         0x061C: 'ARABIC LETTER MARK', 0x034F: 'COMBINING GRAPHEME JOINER', 0x2061: 'FUNCTION APPLICATION',
         0x2062: 'INVISIBLE TIMES', 0x2063: 'INVISIBLE SEPARATOR', 0x2064: 'INVISIBLE PLUS', 0x115F: 'HANGUL CHOSEONG FILLER',
         0x1160: 'HANGUL JUNGSEONG FILLER', 0x3164: 'HANGUL FILLER', 0xFFA0: 'HALFWIDTH HANGUL FILLER', 0xFFFC: 'OBJECT REPLACEMENT'}
INVIS.update({cp: 'VARIATION SELECTOR' for cp in range(0xFE00, 0xFE10)})
INVIS.update({cp: 'VARIATION SELECTOR SUPPLEMENT' for cp in range(0xE0100, 0xE01F0)})
INVIS.update({cp: 'TAG CHARACTER' for cp in range(0xE0000, 0xE0080)})
INVIS.update({cp: 'PRIVATE USE' for cp in range(0xE000, 0xF900)})
SPACES = {0x00A0: 'NBSP', 0x202F: 'NARROW NBSP', 0x2009: 'THIN SPACE', 0x200A: 'HAIR SPACE', 0x2007: 'FIGURE SPACE', 0x3000: 'IDEOGRAPHIC SPACE'}
TRAILERS = [r'🤖[^\n]*', r'Generated (with|by) \[?Claude[^\n]*', r'Co-Authored-By:\s*Claude[^\n]*', r'Claude Code[^\n]*',
            r'[Aa]s an AI( language model)?[^\n]*', r'I hope this helps[^\n]*']
DISCLOSE = re.compile(r'[^.。\n]*(생성형 AI|Claude|Anthropic|ChatGPT|GPT-4|LLM을 사용)[^.。\n]*[.。]?')
MD = [(r'\*\*([^*\n]+)\*\*', r'\1'), (r'(?m)^#{1,6}\s+', ''), (r'```[a-z]*', '')]
DRAFT = re.compile(r'⟦[a-z]?:?|⟧|【|】|\[\[결과 대기\]\]')


def scan(text):
    out = []
    import collections
    c = collections.Counter(ch for ch in text if ord(ch) in INVIS or ord(ch) in SPACES)
    for ch, n in sorted(c.items()):
        cp = ord(ch)
        out.append(f'{INVIS.get(cp) or SPACES.get(cp)} U+{cp:04X}: {n}')
    hits = []
    for pat in TRAILERS:
        for m in re.finditer(pat, text):
            if not any(m.start() >= a and m.end() <= b for a, b in hits):
                hits.append((m.start(), m.end()))
                out.append(f'trailer: {m.group(0)[:80]}')
    n = len(re.findall(r'(?m)\*\*[^*\n]+\*\*|^#{1,6}\s|```', text))
    if n:
        out.append(f'Markdown leftovers: {n}')
    n = len(DRAFT.findall(text))
    if n:
        out.append(f'draft markers (⟦ ⟧ 【 】 [[결과 대기]]): {n}  <- remove only when the values are final')
    n = text.count('—')
    if n:
        out.append(f'em dash —: {n}')
    for m in DISCLOSE.finditer(text):
        if re.search(r'사용|used|use of', m.group(0)) and not re.search('|'.join(TRAILERS), m.group(0)):
            out.append(f'AI-use disclosure (kept, author decides): {m.group(0).strip()[:120]}')
    return out


def clean(text, fix_dashes=False, markdown=False):
    text = ''.join('' if ord(ch) in INVIS else (' ' if ord(ch) in SPACES else ch) for ch in text)
    for pat in TRAILERS:
        text = re.sub(r'\n?' + pat, '', text)
    if markdown:
        for a, b in MD:
            text = re.sub(a, b, text)
    if fix_dashes:
        text = re.sub(r'\s*—\s*', ', ', text)
    return text


def docx(path, fix, author, fix_dashes):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    rep = []
    for n in names:
        if n.startswith('word/') and n.endswith('.xml'):
            s = z.read(n).decode('utf-8')
            t = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', s))
            rep += [f'{n}: {x}' for x in scan(t)]
            for a in sorted(set(re.findall(r'w:author="([^"]*)"', s))):
                rep.append(f'{n}: author "{a}"')
    for n in ('docProps/core.xml', 'docProps/app.xml', 'docProps/custom.xml'):
        if n in names:
            s = z.read(n).decode('utf-8')
            for tag in re.findall(r'<((?:dc|cp|dcterms):[A-Za-z]+|Application|AppVersion|Company|Manager|Template|Pages|Words|TotalTime)[^>]*>([^<]*)<', s):
                rep.append(f'{n}: {tag[0]} = {tag[1][:80]}')
            if 'custom.xml' in n:
                rep.append(f'{n}: custom properties present')
    if not fix:
        return rep
    out = os.path.splitext(path)[0] + ' (정리).docx'
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as w:
        for item in z.infolist():
            b = z.read(item.filename)
            if item.filename == 'docProps/custom.xml':
                continue
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                s = b.decode('utf-8')
                s = re.sub(r'(<w:t[^>]*>)([^<]*)(</w:t>)', lambda m: m.group(1) + clean(m.group(2), fix_dashes) + m.group(3), s)
                s = re.sub(r'w:author="[^"]*"', f'w:author="{author}"', s)
                b = s.encode('utf-8')
            elif item.filename == 'docProps/core.xml':
                s = b.decode('utf-8')
                s = re.sub(r'<dc:creator>[^<]*</dc:creator>', f'<dc:creator>{author}</dc:creator>', s)
                s = re.sub(r'<cp:lastModifiedBy>[^<]*</cp:lastModifiedBy>', f'<cp:lastModifiedBy>{author}</cp:lastModifiedBy>', s)
                s = re.sub(r'<(dc:description|cp:keywords|dc:subject|cp:category)>[^<]*</\1>', r'<\1></\1>', s)
                s = re.sub(r'<cp:revision>[^<]*</cp:revision>', '<cp:revision>1</cp:revision>', s)
                s = re.sub(r'(<dcterms:(?:created|modified)[^>]*>)[^<]*', r'\g<1>' + now, s)
                b = s.encode('utf-8')
            elif item.filename == 'docProps/app.xml':
                s = b.decode('utf-8')
                s = re.sub(r'<(Pages|Words|Characters|CharactersWithSpaces|Lines|Paragraphs|TotalTime)>[^<]*</\1>', '', s)
                s = re.sub(r'<(Company|Manager)>[^<]*</\1>', '', s)
                b = s.encode('utf-8')
            elif item.filename == '[Content_Types].xml':
                b = re.sub(rb'<Override[^>]*PartName="/docProps/custom.xml"[^>]*/>', b'', b)
            elif item.filename == '_rels/.rels':
                b = re.sub(rb'<Relationship[^>]*Target="docProps/custom.xml"[^>]*/>', b'', b)
            w.writestr(item, b)
    rep.append(f'written: {out}')
    return rep


def pdf(path, fix, author):
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(path)
    rep = [f'info {k} = {str(v)[:80]}' for k, v in (r.metadata or {}).items()]
    t = '\n'.join((p.extract_text() or '') for p in r.pages)
    rep += scan(t)
    if r.trailer['/Root'].get('/Metadata') is not None:
        rep.append('XMP metadata present')
    if fix:
        w = PdfWriter(clone_from=r)
        w.metadata = None
        w.add_metadata({'/Author': author, '/Title': (r.metadata or {}).get('/Title', '') or ''})
        if '/Metadata' in w._root_object:
            del w._root_object['/Metadata']
        out = os.path.splitext(path)[0] + ' (정리).pdf'
        with open(out, 'wb') as f:
            w.write(f)
        rep.append(f'written: {out} (page text unchanged; fix the source and rebuild if the text needs cleaning)')
    return rep


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    path, fix = a[0], '--fix' in a
    author = a[a.index('--author') + 1] if '--author' in a else '최성철'
    fix_dashes = '--fix-dashes' in a
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        rep = docx(path, fix, author, fix_dashes)
    elif ext == '.pdf':
        rep = pdf(path, fix, author)
    else:
        s = open(path, encoding='utf-8').read()
        rep = scan(s)
        if fix:
            out = os.path.splitext(path)[0] + ' (정리)' + ext
            open(out, 'w', encoding='utf-8').write(clean(s, fix_dashes, markdown=ext not in ('.md',)))
            rep.append(f'written: {out}')
    print('\n'.join(rep) if rep else 'no traces found')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
