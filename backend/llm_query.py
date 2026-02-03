
from templates.time_resolver import resolve_time_range
from templates.safe_time import extract_time_range_semantic
from templates.time_range import TimeRange
# query = 'total of last year'
# query = 'total bill for last november'
# query='total bill for last 5 months'
# query='bills between september and november 2024'
query='recent bills'
query='total bill amount in 19 jan 2026'
print('--- QUERY ---')
print(query)

print('--- EXTRACT ---')
p = extract_time_range_semantic(query)
print(p)


if p is None:
    print("--- RESOLVE FAILED ---")
    print(None)
else:
    print('--- RESOLVE ---')
    r = resolve_time_range(p)
    print(r)