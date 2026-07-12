# Road-following synthetic fixtures (map-matching tests + sanity notebook)

Same synthetic-.plt rules as `../geolife/README.md` (real Geolife is not
redistributable). Routes are shortest paths in the committed `beijing_fixture`
graph; points every ~25 m at 5 s intervals (18 km/h), gaussian noise sigma=3 m,
seed 20260705. Cleaning keeps every point (dt = resample_s = 5 s).

| traj | orig node | dest node | edges | length m | points |
| --- | --- | --- | --- | --- | --- |
| `geolife_onroad/005/20081201080000` | 1767362150 | 1293134700 | 9 | 713 | 29 |
| `geolife_onroad/005/20081202080000` | 3957692090 | 5929059873 | 22 | 2910 | 117 |
| `geolife_onroad/005/20081203080000` | 4415045593 | 13173248458 | 19 | 2374 | 95 |
| `geolife_onroad/005/20081204080000` | 4611128341 | 1497364615 | 7 | 679 | 27 |
| `geolife_onroad/006/20081205080000` | 1497364698 | 1497364734 | 10 | 726 | 29 |
| `geolife_onroad/006/20081206080000` | 5676070941 | 13173248458 | 12 | 1731 | 70 |
| `geolife_onroad/006/20081207080000` | 4611128341 | 5928928464 | 22 | 2555 | 103 |
| `geolife_onroad/006/20081208080000` | 1573977359 | 2699333615 | 13 | 852 | 34 |
