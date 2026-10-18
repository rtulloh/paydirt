# Chart Generator / Excel Importer

[Documentation index](README.md) · [Seasons and file formats](seasons.md)

## What the Tool Does

[`extract_charts.py`](../extract_charts.py) generates game CSV charts from existing Excel workbooks.
It is a **converter**, not a tool that derives new team ratings from football statistics.
Run it from a source checkout; it is not a browser menu feature or separately packaged executable.

| Output | Contents |
|--------|----------|
| `offense.csv` | Offensive dice rows 10–39, nine play columns, breakaway, QB-time, and fumble entries |
| `defense.csv` | Formations A–F, sub-rows 1–5, and play columns 1–9 |
| `special.csv` | Kickoffs, returns, punts, field goals, and extra points |

It reads BLACK cell backgrounds, RED extra-point backgrounds (written as `NG`),
parentheses-style defense number formats, and fumble recovered/lost ranges from offense column Q.
Numeric extra-point cells are written blank for a good kick; RED cells mark misses.

## Requirements and Input Layout

Install the importer's optional dependency in your active Python environment:

```sh
python -m pip install xlrd==1.2.0
python extract_charts.py --help
```

`xlrd` is needed for importing, not ordinary gameplay. Use **Excel 97–2003 `.xls`** files,
one workbook per team, with sheets named exactly **OFFENSE** and **DEFENSE**.
The importer expects the original chart layout, not arbitrary spreadsheets:

- Offense dice values in B; nine offensive play columns in C–K.
- Offense special columns N–P: breakaway, QB-time, and fumble; fumble-range text in Q.
- Defense formation/sub-row labels on the left and numbered play columns in the chart header.
- Special teams on the DEFENSE sheet in N–T; T supplies dice rows and extra-point color.

Preserve colors and number formats. Converting to CSV first loses that information.
Renaming an `.xlsx` file to `.xls` does not convert it.

## Generating Charts

From the repository root, always supply **both** paths:

```sh
# All .xls workbooks in a directory
python extract_charts.py -i /path/to/workbooks -o /path/to/staging/2026

# One workbook, filename relative to the input directory
python extract_charts.py -i /path/to/workbooks -o /path/to/staging/2026 -t DemoTeam.xls
```

| Option | Meaning |
|--------|---------|
| `-i`, `--input` | Workbook directory |
| `-o`, `--output` | Destination season directory |
| `-t`, `--team` | One workbook filename |

Default paths are developer-specific historical download locations; do not rely on them.
Batch discovery selects lowercase `.xls` filenames. Team folder names come from workbook filenames,
with legacy 1972/1983 prefixes removed and a few legacy mappings applied.
For other years, use `DemoTeam.xls` rather than assuming a year prefix is stripped.

**Generate into staging first.** Existing CSVs are overwritten without confirmation,
and errors can leave partial output. Per-team errors are caught and processing continues:
**zero exit status does not prove every import succeeded**. Check `ERROR processing` messages and row counts.

## Synthetic Workbook Example

This optional example uses constant-value synthetic data, not private charts or a realistic team.
Install `xlwt` only to create this example:

```sh
python -m pip install xlwt==1.3.0
```

Save the following as `make_demo_workbook.py` in a scratch directory outside the repository and run it there:

```python
from pathlib import Path
import xlwt

Path("workbooks").mkdir(exist_ok=True)
book = xlwt.Workbook()
offense = book.add_sheet("OFFENSE")
defense = book.add_sheet("DEFENSE")
for play in range(1, 10):
    offense.write(1, play + 1, play)
    defense.write(1, play + 2, play)
for index, roll in enumerate(range(10, 40)):
    row = index + 2
    offense.write(row, 1, roll)
    for column in range(2, 11):
        offense.write(row, column, 3)
    for column in (13, 14):
        offense.write(row, column, 0)
    offense.write(row, 15, "R")
    defense.write(row, 0, "ABCDEF"[index // 5])
    defense.write(row, 1, index % 5 + 1)
    for column in range(3, 12):
        defense.write(row, column, 0)
    for column, value in enumerate((60, 20, 40, 5, 0, "1-40", roll), start=13):
        defense.write(row, column, value)
offense.write(0, 16, "Fumble Recovered 10-29; Lost Ball 30-39")
book.save("workbooks/DemoTeam.xls")
```

Return to the repository root and import using those scratch paths:

```sh
python extract_charts.py -i /path/to/scratch/workbooks -o /path/to/scratch/2026 -t DemoTeam.xls
```

Expect 30 offense, 30 defense, and 30 special-teams rows in `2026/DemoTeam/`.
Row counts are useful controls, not complete semantic validation.

## Validate and Install

1. Check all three CSVs, their headers, and row counts.
2. Compare representative entries to the workbook: gains/losses, BLACK, parentheses, fumbles,
   special-teams ranges, missed extra points, and empty cells.
3. Load the staged chart from the source checkout:

   ```sh
   python -c "from paydirt.chart_loader import load_team_chart; load_team_chart('/path/to/scratch/2026/DemoTeam'); print('Chart files loaded')"
   ```

4. Add `2026.yaml` beside the team directories. For this demo, copy the public
   `seasons/2026/2026.yaml`. Chart loading alone does not validate season rules.
5. Optionally add fictional `team.yaml` and `roster.json` files using [these formats](seasons.md).
6. Back up existing data, then copy the reviewed season to the [appropriate location](seasons.md#season-data-locations).
7. Select the team and inspect its charts and a practice game. In a source checkout with the demo installed:

   ```sh
   python -m paydirt --play --compact --home 2026/DemoTeam --away 2026/Ironclads
   ```

Do not overwrite the distributed Thunderhawks or Ironclads when experimenting.

## Troubleshooting and Limitations

- **Missing xlrd:** install 1.2.0 with the interpreter used for the script.
- **Missing sheet / index errors:** verify exact sheet names, columns, header placement, and original layout.
- **No teams found:** check `-i` and lowercase `.xls` extensions.
- **Empty formula cells:** `xlrd` does not evaluate formulas. Recalculate/save usable cached results in a spreadsheet application,
  or replace formulas with verified literal values in a copy preserving formatting. Inspect the CSV afterward.
- **Wrong BLACK/extra-point entries:** verify solid BLACK/RED fills survived editing.
- **Partial output:** repair only the affected staged team, rerun, and review every message.
- **Team missing in the app:** check rules YAML and source-versus-bundled data locations.

There is no general chart-validity report, dry-run, overwrite protection, or metadata generator.
Loading successfully is not an accuracy guarantee. Import only authorized workbooks;
keep private sources and generated historical charts local, out of commits and unit fixtures.
