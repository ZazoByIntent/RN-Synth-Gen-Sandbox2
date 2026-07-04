# Synthetic Geolife fixture

**Synthetic data, not real Geolife.** The real dataset is distributed under Microsoft
Research terms that do not clearly permit redistribution, so these 20 trajectories
(5 users × 4) were generated in the exact Geolife v1.3 `.plt` format: 6 header lines,
then `lat,lon,0,alt_ft,days_since_1899-12-30,YYYY-MM-DD,HH:MM:SS` per point (GMT).
Coordinates lie inside the `beijing_fixture` bbox `[116.30, 39.98, 116.32, 39.995]`
so the same fixtures serve the map-matching tests (P2).

Planted defects the cleaning tests assert on:

| traj_id | defect |
| --- | --- |
| `geolife/000/20081023025304` | none — fully deterministic L-shape (known-file parsing test): 100 points, 2 s interval, starts at (39.983, 116.305) 2008-10-23 02:53:04 UTC |
| `geolife/002/20081101020000` | 3 speed-spike points (+0.02° lat ≈ 2.2 km in 2 s ≈ 4000 km/h) at indices 30/60/90 |
| `geolife/004/20081104010000` | only 5 points (fails `min_points`) |
| `geolife/004/20081105010000` | ~70 m total length (fails `min_length_m`) |

All other trajectories are seeded random walks (120 points, 2 s interval, ~20 m steps
≈ 36 km/h) that must survive cleaning. Some points carry altitude `-777` (Geolife's
invalid marker) to exercise the altitude-dropping path.
