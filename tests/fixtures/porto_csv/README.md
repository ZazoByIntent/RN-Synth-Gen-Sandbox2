# Tiny Porto taxi CSV in the Kaggle schema (conversion tests)

`train_tiny.csv` mimics the public Kaggle "Taxi Trajectory Prediction" file
(`train.csv`, ECML/PKDD 2015): the same nine quoted columns (`TRIP_ID, CALL_TYPE,
ORIGIN_CALL, ORIGIN_STAND, TAXI_ID, TIMESTAMP, DAY_TYPE, MISSING_DATA, POLYLINE`),
`POLYLINE` a JSON list of `[lon, lat]` pairs sampled every 15 s. Coordinates are
invented but lie in central Porto. Used by `tests/test_ldptrace_dat.py` to exercise
`convert_porto` (`src/trajguard/datasets/ldptrace_dat.py`) with the default bbox
`(-8.64, 41.14, -8.60, 41.17)` (central Porto, `PORTO_CENTRE_BBOX`).

| row | TRIP_ID | points | outcome | reason |
| --- | --- | --- | --- | --- |
| 1 | 1372636858620000589 | 3 | kept | inside bbox |
| 2 | 1372637303620000596 | 2 | kept | inside bbox, minimum length |
| 3 | 1372636951620000320 | 4 | kept | inside bbox |
| 4 | 1372636854620000520 | 2 | dropped | `MISSING_DATA = "True"` |
| 5 | 1372637091620000337 | 1 | dropped | fewer than two points |
| 6 | 1372636965620000231 | 3 | dropped | second point at lon −8.7, outside the bbox |

The three kept trajectories have 9 points; their bbox is lon `−8.630351 … −8.612964`,
lat `41.140278 … 41.159871`, so `grid_bbox` in `porto_stats.json` is that bbox widened
by `1e-6` on every side.
