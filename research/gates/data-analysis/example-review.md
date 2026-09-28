# Synthetic notebook review

## Reviewer and source

Reviewer: Codex `gpt-6-astra` at medium effort, distinct from the `gpt-6-sol` implementer. The review read issue #107, the issue #104 verification protocol, and the uncommitted source on branch `research/107-activate-the-analysis-notebook` at base commit `b041b064b0fb465ba39c9fcf7058368081efe04e` on 2026-09-27. The input SHA-256 was `4c9cde4c5fd18049b0546787cc50cd8ce1d15aab567e09347cceacd6706747fa`.

## Attempted rerun

`mise run notebooks:verify -- research/gates/data-analysis/example.qmd` exited 1 before Python execution when the first pinned Quarto installation was denied. A separate `mise exec -- python -c '<CSV and sample recomputation>'` attempt also exited 1 before Python execution for that install denial. Mise later installed Quarto normally, but the notebook render was still blocked by the sandboxed macOS Quarto log and Jupyter transport directories. The reviewer did not claim a Quarto rerun.

## Manual source inspection

The reviewer then used `mise exec -- uv run --group analysis python -` with an independent stdin script that parsed the inspected unquoted synthetic CSV by direct comma splitting and summed values with `Decimal`. It did not call DuckDB, `csv.DictReader`, or the notebook code. The command exited 0. The independent total is 48 minutes across twelve rows. Category A is 21 minutes across six rows, and category B is 27 minutes across six rows. Each result and denominator matches `example-results.csv` and `example-claims.csv` with zero difference.

The full SHA-256 sample ordering under issue ID 107 is `E04,E06,E03,E11,E07,E01,E05,E02,E10,E12,E08,E09`. The selected ten supporting rows were independently recomputed as follows.

| Row ID | Category | Minutes | Difference |
| --- | --- | ---: | ---: |
| E04 | A | 4 | 0 |
| E06 | A | 6 | 0 |
| E03 | A | 3 | 0 |
| E11 | B | 6 | 0 |
| E07 | B | 2 | 0 |
| E01 | A | 1 | 0 |
| E05 | A | 5 | 0 |
| E02 | A | 2 | 0 |
| E10 | B | 5 | 0 |
| E12 | B | 7 | 0 |

The reviewer parsed both final SVGs with Python XML tools through `mise exec -- uv run --group analysis python -`. The command exited 0. Each chart has one A bar and one B bar, with values 21 and 27 encoded against a 0 to 32 minute axis. The marks have a common y baseline of 174.2, with top positions 66.96875 and 36.33125. Both variants contain the expected category names, value labels, axis labels, and ticks. The x-axis label baseline is 202.797656 inside the 216-unit canvas after the clipping fix. The reviewer found no omitted or extra group bar and zero encoding differences. After the later accessibility title and generic-font change, the reviewer reran the same command with exit 0 and found unchanged bar values, geometry, and labels. The final light SVG SHA-256 is `654cfcf8af1850c4466812843251e670badbf469872e68a8677df81ea9fc3248`. The final dark SVG SHA-256 is `b2165d1d60a3725b81723b68529e75c1032fb838711b5e58762cadb6c75e82a3`. The review did not include a raster or browser visual inspection.

## Commands retained

The reviewer ran this command before the SVG layout fix. Its numerical and sample output remains valid, while its chart geometry output describes the superseded SVGs.

```sh
mise exec -- uv run --group analysis python - <<'PY'
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
import xml.etree.ElementTree as ET
import re

base = Path('research/gates/data-analysis')
raw = (base / 'example-data.csv').read_bytes()
lines = raw.decode().splitlines()
assert lines[0] == 'id,category,minutes'
records = [line.split(',') for line in lines[1:]]
assert len({row[0] for row in records}) == len(records)
print('INPUT_SHA256', sha256(raw).hexdigest())
results = {fields[0]: fields[1:] for fields in [line.split(',') for line in (base / 'example-results.csv').read_text().splitlines()[1:]]}
claims = {fields[0]: fields for fields in [line.split(',') for line in (base / 'example-claims.csv').read_text().splitlines()[1:]]}
for cid, rid, category in [('N-01', 'TOTAL', None), ('N-02', 'G-A', 'A'), ('N-03', 'G-B', 'B')]:
    population = [Decimal(value) for _, group, value in records if category is None or group == category]
    value = sum(population, Decimal(0))
    denominator = len(population)
    assert Decimal(results[rid][2]) == value
    assert Decimal(claims[cid][3]) == value
    assert int(claims[cid][6]) == denominator
    print('CLAIM', cid, 'value', value, 'denominator', denominator, 'difference', Decimal(results[rid][2]) - value)
ordered = sorted({row[0] for row in records}, key=lambda rid: (sha256(('107|' + rid).encode()).hexdigest(), rid))
print('COMPLETE_ORDER', ','.join(ordered))
for rid in ordered[:10]:
    _, category, value = next(row for row in records if row[0] == rid)
    assert results[rid] == ['supporting', category, value]
    print('SAMPLE', rid, category, value, 'difference 0')
ns = {'s': 'http://www.w3.org/2000/svg'}
for theme in ('light', 'dark'):
    path = base / f'example-chart-{theme}.svg'
    source = path.read_text()
    root = ET.fromstring(source)
    print('CHART', path.name, 'SHA256', sha256(path.read_bytes()).hexdigest(), 'viewBox', root.attrib['viewBox'])
    for group in root.findall('.//s:g', ns):
        gid = group.get('id', '')
        if gid in {'patch_2','patch_3','patch_4'}:
            print(gid, [p.attrib for p in group.findall('s:path', ns)])
        if gid.startswith('text_'):
            segment = re.search(r'<g id="' + gid + r'">(.*?)</g>', source, re.S).group(1)
            print(gid, re.findall(r'<!--\s*(.*?)\s*-->', segment), re.findall(r'transform="([^"]+)"', segment)[:1])
PY
```

The reviewer ran this command after the SVG layout fix and again after the accessibility title and font change. It checks both current variants and exited 0 in each run.

```sh
mise exec -- uv run --group analysis python - <<'PY'
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
import re
import xml.etree.ElementTree as ET
ns = {'s':'http://www.w3.org/2000/svg'}
for theme in ('light', 'dark'):
    p = Path(f'research/gates/data-analysis/example-chart-{theme}.svg')
    root = ET.parse(p).getroot()
    print(theme, sha256(p.read_bytes()).hexdigest(), 'viewBox', root.get('viewBox'))
    for t in root.findall('.//s:text', ns):
        print('TEXT', ''.join(t.itertext()), 'x', t.get('x'), 'y', t.get('y'), 'transform', t.get('transform'))
    geometry = {}
    for gid in ('patch_2', 'patch_3', 'patch_4'):
        path = root.find(f'.//s:g[@id="{gid}"]/s:path', ns)
        xy = [Decimal(x) for x in re.findall(r'-?\d+(?:\.\d+)?', path.get('d'))]
        geometry[gid] = (min(xy[0::2]), max(xy[0::2]), min(xy[1::2]), max(xy[1::2]))
        print(gid, geometry[gid], path.get('style'))
    _, _, top, bottom = geometry['patch_2']
    for gid, row, expected in [('patch_3', 'G-A', 21), ('patch_4', 'G-B', 27)]:
        _, _, bar_top, bar_bottom = geometry[gid]
        encoded = (bar_bottom-bar_top) * 32 / (bottom-top)
        difference = encoded - expected
        assert abs(difference) < Decimal('0.000001')
        print(row, 'encoded', encoded, 'difference', difference)
PY
```

## Reviewer execution of Python cells

The reviewer independently executed all three Python cells in notebook order with `uv run --locked --group analysis`. The command below exited 0. It ran the DuckDB query, the notebook's independent CSV method, and chart generation, then checked the regenerated artifacts with separate parsing and Decimal arithmetic. All three cells passed. Claims N-01, N-02, and N-03 matched their result rows and denominators with zero differences. The ten sampled rows matched the retained sample above. Both regenerated SVGs retained their labels and numerical encoding. The latest hashes below include the whitespace normalization.

Matplotlib reported that its default cache directory was not writable and selected a temporary cache directory itself. Fontconfig also reported unwritable cache directories before Matplotlib built its font cache. The reviewer set only the noninteractive `Agg` backend. No host path override was used. Execution completed despite those warnings.

This is direct Python cell execution, not a Quarto or Jupyter render. It verifies the notebook calculations, claim assertions, and generated SVG source. It does not test Quarto cell options, Jupyter execution, HTML output, privacy gates, CI selection, or browser and raster presentation.

```sh
mise exec -- uv run --locked --group analysis python - <<'PY'
import os
import re
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
import xml.etree.ElementTree as ET

notebook = Path("research/gates/data-analysis/example.qmd").resolve()
source = notebook.read_text()
cells = re.findall(r"^```\{python\}\n(.*?)^```\s*$", source, re.M | re.S)
assert len(cells) == 3
os.environ["MPLBACKEND"] = "Agg"
os.chdir(notebook.parent)
namespace = {"__name__": "__main__"}
for number, cell in enumerate(cells, 1):
    exec(compile(cell, f"{notebook.name}:cell-{number}", "exec"), namespace)
    print("CELL", number, "PASS")

records = [line.split(",") for line in Path("example-data.csv").read_text().splitlines()[1:]]
results = {r[0]: r[1:] for r in [line.split(",") for line in Path("example-results.csv").read_text().splitlines()[1:]]}
claims = {r[0]: r for r in [line.split(",") for line in Path("example-claims.csv").read_text().splitlines()[1:]]}
for cid, rid, category in [("N-01", "TOTAL", None), ("N-02", "G-A", "A"), ("N-03", "G-B", "B")]:
    values = [Decimal(value) for _, group, value in records if category is None or group == category]
    expected = sum(values, Decimal(0))
    assert Decimal(results[rid][2]) == expected == Decimal(claims[cid][3])
    assert len(values) == int(claims[cid][6])
    print("CLAIM", cid, rid, expected, "denominator", len(values), "difference 0")
sample = sorted({r[0] for r in records}, key=lambda rid: (sha256(("107|" + rid).encode()).hexdigest(), rid))[:10]
for rid in sample:
    _, category, value = next(r for r in records if r[0] == rid)
    assert results[rid] == ["supporting", category, value]
    print("SAMPLE", rid, category, value, "difference 0")
ns = {"s": "http://www.w3.org/2000/svg"}
for theme in ("light", "dark"):
    path = Path(f"example-chart-{theme}.svg")
    root = ET.parse(path).getroot()
    labels = ["".join(t.itertext()) for t in root.findall(".//s:text", ns)]
    assert labels == ["A", "B", "Category", "0", "5", "10", "15", "20", "25", "30", "Minutes", "21", "27"]
    assert root.find("s:title", ns).text == "Synthetic category duration"
    geometry = {}
    for gid in ("patch_2", "patch_3", "patch_4"):
        mark = root.find(f'.//s:g[@id="{gid}"]/s:path', ns)
        xy = [Decimal(x) for x in re.findall(r"-?\d+(?:\.\d+)?", mark.get("d"))]
        geometry[gid] = (min(xy[1::2]), max(xy[1::2]))
    top, bottom = geometry["patch_2"]
    for gid, rid in [("patch_3", "G-A"), ("patch_4", "G-B")]:
        bar_top, bar_bottom = geometry[gid]
        encoded = (bar_bottom - bar_top) * 32 / (bottom - top)
        assert encoded == Decimal(results[rid][2])
        print("CHART", theme, rid, encoded, "difference 0")
    print("SVG", theme, "SHA256", sha256(path.read_bytes()).hexdigest(), "viewBox", root.get("viewBox"), "labels", labels)
print("INPUT_SHA256", sha256(Path("example-data.csv").read_bytes()).hexdigest())
PY
```

The command produced the following results after the cache warnings.

```text
CELL 1 PASS
Sample row IDs: E04, E06, E03, E11, E07, E01, E05, E02, E10, E12
Independent headline: 48
CELL 2 PASS
CELL 3 PASS
CLAIM N-01 TOTAL 48 denominator 12 difference 0
CLAIM N-02 G-A 21 denominator 6 difference 0
CLAIM N-03 G-B 27 denominator 6 difference 0
SAMPLE E04 A 4 difference 0
SAMPLE E06 A 6 difference 0
SAMPLE E03 A 3 difference 0
SAMPLE E11 B 6 difference 0
SAMPLE E07 B 2 difference 0
SAMPLE E01 A 1 difference 0
SAMPLE E05 A 5 difference 0
SAMPLE E02 A 2 difference 0
SAMPLE E10 B 5 difference 0
SAMPLE E12 B 7 difference 0
CHART light G-A 21.0000 difference 0
CHART light G-B 27.0000 difference 0
SVG light SHA256 654cfcf8af1850c4466812843251e670badbf469872e68a8677df81ea9fc3248 viewBox 0 0 360 216 labels ['A', 'B', 'Category', '0', '5', '10', '15', '20', '25', '30', 'Minutes', '21', '27']
CHART dark G-A 21.0000 difference 0
CHART dark G-B 27.0000 difference 0
SVG dark SHA256 b2165d1d60a3725b81723b68529e75c1032fb838711b5e58762cadb6c75e82a3 viewBox 0 0 360 216 labels ['A', 'B', 'Category', '0', '5', '10', '15', '20', '25', '30', 'Minutes', '21', '27']
INPUT_SHA256 4c9cde4c5fd18049b0546787cc50cd8ce1d15aab567e09347cceacd6706747fa
```

## SVG whitespace normalization

The notebook now strips trailing whitespace from each generated SVG line and retains a final newline. The reviewer reran the exact three-cell command above with `--locked`, and it exited 0. All three cells passed again, the claim values and denominators matched, and all ten supporting rows had zero differences. Both SVGs still encode A = 21 and B = 27 minutes with zero differences, the same labels, and the same 360 by 216 canvas. The output above records this latest run and its normalized-file hashes.

The following additional check exited 0. It confirmed that neither SVG contains trailing whitespace, both end in a newline, and the Category label baseline remains at 202.797656.

```sh
mise exec -- uv run --locked --group analysis python - <<'PY'
from pathlib import Path
from hashlib import sha256
import xml.etree.ElementTree as ET
ns = {"s": "http://www.w3.org/2000/svg"}
for theme in ("light", "dark"):
    path = Path(f"research/gates/data-analysis/example-chart-{theme}.svg")
    data = path.read_bytes()
    assert data.endswith(b"\n")
    assert all(line == line.rstrip() for line in data.splitlines())
    root = ET.fromstring(data)
    category = next(t for t in root.findall(".//s:text", ns) if t.text == "Category")
    assert category.get("y") == "202.797656"
    print(theme, "trailing whitespace absent; final newline present; Category y=202.797656", sha256(data).hexdigest())
PY
```

```text
light trailing whitespace absent; final newline present; Category y=202.797656 654cfcf8af1850c4466812843251e670badbf469872e68a8677df81ea9fc3248
dark trailing whitespace absent; final newline present; Category y=202.797656 b2165d1d60a3725b81723b68529e75c1032fb838711b5e58762cadb6c75e82a3
```

## Findings and resolution

The first review found that the chart code read the in-memory DuckDB result instead of the committed aggregate table, the prose said twelve supporting rows were sampled when the protocol selects ten, and CI did not compare the regenerated result table to the committed table. The implementation now reads the chart source rows from `example-results.csv`, names ten sampled rows, and checks the table diff in CI. The review also found that the claim ledger and denominators were not asserted, the privacy scan omitted output artifacts, and private-input notebooks had no CI exclusion marker. The implementation now asserts claim values and denominators, scans adjacent CSV and SVG files plus public rendered HTML, and reserves `private-input: true` for local-only rendering. Direct Python execution verified the notebook calculations and claim assertions. The privacy and CI changes remain source-inspection findings in this review.

## Pending checks

Quarto notebook execution remains blocked locally. A clean CI run must still rerender the notebook through its pinned Jupyter engine, and the reviewer must confirm that run and inspect the displayed charts before full approval. The current review verifies direct Python cell execution, independent numerical results, and SVG source encoding.
