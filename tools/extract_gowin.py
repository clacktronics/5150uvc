import sys, csv, pymupdf
doc = pymupdf.open(sys.argv[1])
rows = []
for page in doc:
    for t in page.find_tables():
        for r in t.extract():
            if r and r[0] and r[0] != 'Pin Name':
                rows.append([ (c or '').replace('\n',' ').strip() for c in r])
w = csv.writer(open(sys.argv[2], 'w', newline=''))
for r in rows: w.writerow(r)
print(len(rows))
