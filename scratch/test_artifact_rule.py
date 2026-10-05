import pymupdf
import re
from pathlib import Path

def test_file_for_artifacts(filepath):
    doc = pymupdf.open(str(filepath))
    print(f"=== TESTING FILE: {Path(filepath).name} (Pages: {len(doc)}) ===")
    
    token_pattern = re.compile(r'(/(\w+)\s+(<<.*?>>)\s*BDC|/(\w+)\s+BMC|(\bEMC\b)|(/(\w+)\s+Do))', re.DOTALL)
    art_count_pattern = re.compile(r'/Artifact\s*(?:<<.*?>>)?\s*B[DM]C', re.DOTALL)
    
    total_passed = 0
    total_failed = 0
    failures = []
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1
        contents = page.get_contents()
        if not contents:
            continue
        stream = '\n'.join([doc.xref_stream(x).decode('latin1', errors='ignore') for x in contents])
        
        # XObject name to (xref, rect)
        xobj_info = {}
        for xo in page.get_xobjects():
            xobj_info[xo[1]] = {'xref': xo[0], 'rect': xo[3]}
            
        stack = [] # list of dicts: {'tag': str, 'mcid': Optional[int]}
        
        for m in token_pattern.finditer(stream):
            full = m.group(1)
            if 'BDC' in full:
                tag = m.group(2)
                props = m.group(3)
                mcid = None
                if '/MCID' in props:
                    mc_match = re.search(r'/MCID\s+(\d+)', props)
                    if mc_match:
                        mcid = int(mc_match.group(1))
                is_art = (tag.lower() == 'artifact')
                in_tagged = any(s['mcid'] is not None for s in stack)
                
                if is_art:
                    if in_tagged:
                        total_failed += 1
                        ancestor = next(s for s in reversed(stack) if s['mcid'] is not None)
                        failures.append((page_num, tag, ancestor['tag'], ancestor['mcid'], None, None))
                    else:
                        total_passed += 1
                stack.append({'tag': tag, 'mcid': mcid})
                
            elif 'BMC' in full:
                tag = m.group(4)
                is_art = (tag.lower() == 'artifact')
                in_tagged = any(s['mcid'] is not None for s in stack)
                if is_art:
                    if in_tagged:
                        total_failed += 1
                        ancestor = next(s for s in reversed(stack) if s['mcid'] is not None)
                        failures.append((page_num, tag, ancestor['tag'], ancestor['mcid'], None, None))
                    else:
                        total_passed += 1
                stack.append({'tag': tag, 'mcid': None})
                
            elif full == 'EMC':
                if stack:
                    stack.pop()
                    
            elif 'Do' in full:
                xname = m.group(7)
                in_tagged = any(s['mcid'] is not None for s in stack)
                if xname in xobj_info:
                    xo_entry = xobj_info[xname]
                    xref = xo_entry['xref']
                    rect = xo_entry['rect']
                    try:
                        xo_stream = doc.xref_stream(xref).decode('latin1', errors='ignore')
                        xo_arts = len(art_count_pattern.findall(xo_stream))
                        if in_tagged:
                            total_failed += xo_arts
                            ancestor = next(s for s in reversed(stack) if s['mcid'] is not None)
                            for _ in range(xo_arts):
                                failures.append((page_num, f"XObject:{xname}", ancestor['tag'], ancestor['mcid'], xref, rect))
                        else:
                            total_passed += xo_arts
                    except Exception as e:
                        pass
                        
    print(f"  Passed artifacts outside tagged content: {total_passed}")
    print(f"  Failed artifacts inside tagged content : {total_failed}")
    print(f"  Total failures recorded               : {len(failures)}")
    if failures:
        # Group by page
        page_counts = {}
        for f in failures:
            page_counts[f[0]] = page_counts.get(f[0], 0) + 1
        print(f"  Failure distribution across {len(page_counts)} pages:")
        for p, cnt in sorted(page_counts.items()):
            sample = next(f for f in failures if f[0] == p)
            print(f"    Page {p:2d}: {cnt} error(s) | Parent: <{sample[2]}> MCID={sample[3]} | XObject={sample[0]} BBox={sample[5]}")

test_files = [
    r"C:\Users\HBS\Downloads\Work_Documentation_Administrative_Fillable_1_accessible.pdf",
    r"C:\Users\HBS\Downloads\58-78 (2).pdf",
    r"C:\Users\HBS\Downloads\SF_Chapter 16 202-269.pdf",
    r"C:\Users\HBS\Downloads\miller-cacs1e-ch02.02_updated (1).pdf",
    r"test_samples\accessible_sample.pdf",
    r"test_samples\inaccessible_untagged_sample.pdf"
]

for tf in test_files:
    if Path(tf).exists():
        test_file_for_artifacts(tf)
