"""Compare two SpoQC output folders, e.g. upstream dev and a change branch run on the same input.

    python fork/equivalence/compare_outputs.py <reference spoQC_tmp> <candidate spoQC_tmp> [--exact] [--csv out.csv]

Compares every output both folders have, column by column:
  * parquet files and parquet folders (part.N.parquet, read in part order), e.g. the HQPR/HQTR/HQCR masks
  * .csv / .tsv tables
Per numeric column it reports the share of identical values, the largest absolute difference and the Pearson
correlation; per integer or boolean column with at most 10 distinct values (masks, labels) the share of rows that agree.
Rows are compared by position, so both runs must cover the same pixels or cells in the same order.

--exact   exit with status 1 if anything differs (for changes that should give identical results)
--csv     also write the table to a CSV file
Outputs only one folder has are listed, not compared.
"""
import argparse, glob, os, sys
import numpy as np, pandas as pd, pyarrow.parquet as pq

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("reference"); ap.add_argument("candidate")
ap.add_argument("--exact", action="store_true"); ap.add_argument("--csv")
ap.add_argument("--rtol", type=float, default=0.0, help="relative tolerance counted as identical (default 0)")
args = ap.parse_args()


def outputs(root):
    """Relative names of comparable outputs: parquet files/folders and csv/tsv tables."""
    found = {}
    for path in sorted(glob.glob(os.path.join(root, "**", "*"), recursive=True)):
        rel = os.path.relpath(path, root)
        if os.path.isdir(path) and glob.glob(os.path.join(path, "*.parquet")):
            found[rel] = ("parquet_dir", path)
        elif path.endswith(".parquet") and os.path.isfile(path) and not glob.glob(os.path.join(os.path.dirname(path), "part.*.parquet")):
            found[rel] = ("parquet", path)
        elif path.endswith((".csv", ".tsv")) and os.path.isfile(path):
            found[rel] = ("table", path)
    return found


def parquet_parts(kind, path):
    if kind == "parquet":
        return [path]
    files = glob.glob(os.path.join(path, "*.parquet"))
    def order(f):
        stem = os.path.basename(f).rsplit(".", 1)[0]
        return int(stem.split(".")[-1]) if stem.split(".")[-1].isdigit() else stem
    return sorted(files, key=order)


def columns(kind, path):
    if kind == "table":
        return list(pd.read_csv(path, sep=None, engine="python", nrows=5).columns)
    return pq.ParquetFile(parquet_parts(kind, path)[0]).schema_arrow.names


def column(kind, path, name):
    if kind == "table":
        return pd.read_csv(path, sep=None, engine="python", usecols=[name])[name].to_numpy()
    return np.concatenate([pq.read_table(f, columns=[name]).column(0).to_numpy(zero_copy_only=False)
                           for f in parquet_parts(kind, path)])


def compare(a, b):
    row = {"n": len(a)}
    if len(a) != len(b):
        return {**row, "status": f"different length ({len(a)} vs {len(b)})", "identical": False}
    if a.dtype.kind in "OUSb" or b.dtype.kind in "OUSb" or (a.dtype.kind in "iu" and len(np.unique(a[: 100000])) <= 10):
        agree = float(np.mean(a.astype(str) == b.astype(str))) if a.dtype.kind in "OUS" else float(np.mean(a == b))
        return {**row, "agree": agree, "identical": agree == 1.0, "status": "categorical"}
    a, b = a.astype(np.float64), b.astype(np.float64)
    both_nan = np.isnan(a) & np.isnan(b)
    same = both_nan | np.isclose(a, b, rtol=args.rtol, atol=0.0) if args.rtol else both_nan | (a == b)
    ok = ~(np.isnan(a) | np.isnan(b))
    diff = np.abs(a[ok] - b[ok])
    corr = float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 2 and a[ok].std() > 0 and b[ok].std() > 0 else np.nan
    return {**row, "agree": float(same.mean()), "max_abs_diff": float(diff.max()) if diff.size else 0.0,
            "mean_abs_diff": float(diff.mean()) if diff.size else 0.0, "pearson_r": corr,
            "identical": bool(same.all()), "status": "numeric"}


ref, cand = outputs(args.reference), outputs(args.candidate)
rows = []
for name in sorted(set(ref) | set(cand)):
    if name not in ref or name not in cand:
        rows.append({"output": name, "column": "", "status": f"only in {'reference' if name in ref else 'candidate'}", "identical": False})
        continue
    (ka, pa), (kb, pb) = ref[name], cand[name]
    ca, cb = columns(ka, pa), columns(kb, pb)
    for col in [c for c in ca if c in cb]:
        try:
            rows.append({"output": name, "column": col, **compare(column(ka, pa, col), column(kb, pb, col))})
        except Exception as err:  # keep going; report what couldn't be compared
            rows.append({"output": name, "column": col, "status": f"error: {err}", "identical": False})
    for col in sorted(set(ca) ^ set(cb)):
        rows.append({"output": name, "column": col, "status": f"column only in {'reference' if col in ca else 'candidate'}", "identical": False})

table = pd.DataFrame(rows)
with pd.option_context("display.max_rows", None, "display.width", 200, "display.float_format", "{:.6g}".format):
    print(table.to_string(index=False))
if args.csv:
    table.to_csv(args.csv, index=False)
n_diff = int((~table.identical.astype(bool)).sum())
print(f"\n{len(table)} compared, {len(table) - n_diff} identical, {n_diff} different or not comparable.")
sys.exit(1 if args.exact and n_diff else 0)
