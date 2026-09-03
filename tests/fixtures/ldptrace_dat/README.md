# Hand-written `.dat` fixture in the LDPTrace reference format

`tiny.dat` holds five trajectories in the text format the LDPTrace reference code
(github.com/zealscott/LDPTrace, `read_brinkhoff`) reads: one `#<id>:` line followed
by one `>0: x,y;x,y;...;` line per trajectory, coordinates as `lon,lat` (x, y) in
whatever unit the file uses — here plain numbers in the bbox `0..6 × 0..6`. Read by
`LDPTraceDatLoader` (`src/trajguard/datasets/ldptrace_dat.py`) and used by the
`bbox` mode of `LDPTraceGenerator` in `tests/test_ldptrace.py`.

Cells below refer to `Grid(bbox=(0, 0, 6, 6), n_rows=6, n_cols=6)`, row-major index
`row · 6 + col` with the row from y (lat) and the column from x (lon). Every
coordinate sits at a cell centre (half-integers), so the cell of `(x, y)` is
`int(y) · 6 + int(x)` with no boundary ambiguity.

| id | points (x,y) | cells per point | chain after `Grid.chain` | planted feature |
| --- | --- | --- | --- | --- |
| 0 | (0.5,0.5) (1.5,0.5) (2.5,1.5) | 0, 1, 8 | `[0, 1, 8]` | already 8-adjacent, unchanged |
| 1 | (0.5,0.5) (3.5,1.5) | 0, 9 | `[0, 7, 8, 9]` | non-adjacent jump → king's walk inserts 7, 8 |
| 2 | (2.5,2.5) | 14 | `[14]` | single point |
| 3 | (4.5,4.5) (4.6,4.4) (5.5,5.5) | 28, 28, 35 | `[28, 35]` | repeated cell collapsed |
| 4 | (5.5,0.5) (4.5,1.5) (3.5,2.5) (2.5,3.5) | 5, 10, 15, 20 | `[5, 10, 15, 20]` | diagonal steps |

13 points in total. The loader assigns `user_id = "<id>"`, `traj_id =
"ldptrace_dat/<id>"` and synthetic timestamps `0, dt_s, 2·dt_s, …` (default 15 s).
