# Review of P0–P5 — open concerns for a later pass

Reviewer pass over the linear branch stack `main → …P0… → claude/p5-geoind`
(everything unmerged, reviewed at commit `452fff3`). **Verdict: the stack is
clean, disciplined, and faithful to the design + CLAUDE.md. Toolchain green
(ruff / ruff format / mypy --strict / 92 pytest all pass), the vertical slice
runs end to end, and the reidentification / geo-ind results are internally
consistent.** Nothing below blocks P6. This file records the concerns so they
are not lost; none is a live crash in the current single-map, fixture-scale path.

Severity legend: **[C]** latent correctness · **[R]** robustness / clarity ·
**[M]** methodology (for the write-up, not a code bug) · **[P6]** affects the
next phase.

---

## Latent correctness

- **[C] `id(net)` as the matcher context cache key** — `matching/leuven.py:33`
  (also used at `:107`, `:126-127`). `RoadNetwork` is an unhashable frozen
  dataclass, so `id()` is the workaround, but the cache holds no reference to
  `net`; after GC, CPython can reuse the address for a *different* network and a
  stale entry is served → silently matching against the wrong map. Also never
  evicts. Safe today (one network per run, one memoized matcher in
  `_net_provider`), a real footgun the first time a matcher instance is reused
  across regions (Beijing → Porto). Fix: key on `net.map_id` / region, or cache
  on the network object itself.

- **[C] Empty-trajectory guard is positioned after the match call** —
  `matching/leuven.py:51` calls `matcher.match([])` before the
  `... if traj.points else 0.0` guard at `:76`. A 0-point input raises
  `IndexError` inside leuven instead of returning `match_score=0.0` as the P2
  contract states. Currently unreachable (cleaning enforces `min_points ≥ 20`,
  single-point is safe), but move the empty check ahead of the match call to
  honor the contract.

- **[C/P6] Small-N `by_user` splits silently yield empty partitions** —
  `datasets/split.py` (largest-remainder apportionment, ~`:46-54`). The
  apportionment is correct and sums to `n`, but with fewer users than splits a
  whole split becomes empty with no warning. Verified: the `geolife_onroad`
  fixture (2 users) → `train=1, test=1, shadow=0, attack=0`. This directly
  bites P6 MIA (needs a populated `shadow` split). Add a loud check, or a
  MIA-specific fixture/split. See P6 readiness below.

## Robustness / clarity (not live bugs)

- **[R] `mean_speed` unit is implicit and mixed** — `datasets/cleaning.py:78`
  stores `length_m / duration_s` (**m/s**) while the cleaning filter threshold
  is **km/h** (`:51`). Confirmed nothing ever compares them (grep: `mean_speed`
  is only serialized to Parquet, never read), so no bug — but put the unit in
  the field name or a docstring before something downstream trusts it.

- **[R] `osm.py` edge-column selection is unguarded** — `maps/osm.py:114` does
  `edges[_EDGE_COLS]` directly, unlike the guarded node path (`:107`). If an OSM
  extract omits `oneway` (essentially always present on `drive` networks) this
  raises `KeyError`. Mirror the node-side `[c for c in _EDGE_COLS if c in ...]`.

- **[R] `params_hash(default=str)` is only stable for JSON-native params** —
  `privacy/base.py:14`. Fine for all current callers (numbers / strings / lists),
  but `default=str` silently makes the hash non-reproducible for any value with
  an identity-based `repr`. Worth a comment since the docstring promises
  stability; tighten if non-native params ever appear.

- **[R] Zero-value edge cases raise** — `gps_error_m == 0` →
  `ZeroDivisionError` in the leuven score denominator (`matching/leuven.py:79`);
  a zero-extent grid bbox → `ZeroDivisionError` in `Grid.cell_of`
  (`representation/views.py:24-25`). Misconfiguration-only (defaults are safe).

- **[R] `osm.py` provenance / validation** — `osm_timestamp` records the OSMnx
  *download* time, not the OSM data snapshot (`:94`); `load()` reads `region` /
  `crs` from `meta.json` but never checks them against the config (`:64-78`), so
  config drift after a build is silent. Minor reproducibility gaps.

## Methodology notes (for the doctoral write-up)

- **[M] ε=0.1 "protects" by destroying the release, not by defeating the
  attack.** At strong noise the whole release fails re-matching (empty pool) and
  reidentification top-1 reads 0.0. This is handled *correctly* (utility is
  measured on the full noisy release, probes are fixed, drops are recorded in
  `run.json` as `n_rematch_dropped`), but "0.0" there means "no data survived",
  a different privacy claim than "attack failed on noisy data". The single most
  important interpretation nuance for the report — state it explicitly and lean
  on the utility columns to tell the destruction story.

- **[M] DTW is unnormalized** — `attacks/reidentification.py:113` (`_dtw`). The
  accumulated cost grows with path length, biasing nearest-neighbour linkage
  toward shorter gallery trajectories. Defensible as a baseline; note it, or
  normalise by path length if it matters.

- **[M] `linkage_rate` ≡ `top1_acc`** — both are the rank-1 indicator
  (`evaluation/metrics.py`). Redundant but both requested in design §8; keep,
  just don't report them as independent evidence.

- **[M] `spent_budget` is ε·(all points in the whole release)** —
  `privacy/geoind.py:57,69`, accumulated on one shared instance across every
  trajectory in the run. It is a naive-composition diagnostic, not a
  per-trajectory budget; the number is large by construction. Documented, fine
  as a diagnostic — just don't read it as a per-user guarantee.

## P6 readiness (hooks + landmines confirmed)

- **Fixture is too small for MIA.** `geolife_onroad` (2 users) leaves `shadow`
  and `attack` empty (see [C/P6] above). LiRA-lite shadow training needs data;
  plan to (a) grow the on-road fixture with more users, or (b) build MIA /
  reconstruction tests on hand-constructed `MatchedTrajectory` edge sequences
  (as `test_reidentification.py::POOL` already does) rather than the pipeline
  split. Option (b) is cleaner for deterministic unit tests.

- **`_attack_specs` still rejects `target_scope: synthetic`** —
  `experiments/orchestrator.py:124-130` ("synthetic targets land in a later
  phase"). Orchestrator wiring of a `synthetic:<ref>` pool (fitted generator on
  the train split) is out of the strict P6 prompt scope — the three classes +
  fixture tests are the DoD. Lift this only when wiring MIA into the orchestrator.

- **Generator registration.** Nothing registers `kind="generator"` yet;
  `experiments/builtins.py` must import the new `synthesis/markov.py` for its
  `@register` to run (mirrors every other impl).

- **Promote `_dtw` to a shared module.** It lives module-level in
  `attacks/reidentification.py`; the reconstruction attack needs DTW + Hausdorff
  and MIA-adjacent code may want it too. Lift it (e.g. `evaluation/distances.py`)
  instead of duplicating, and add Hausdorff there.

- **MIA metrics are score-based, not per-probe 0/1** — they do not fit
  `SampledMetric`. Follow the `evaluation/utility.py` precedent (name-dispatched
  plain functions). AUC + TPR@FPR can be numpy-only (sort scores, trapezoid);
  avoid a scikit-learn dependency unless justified.

- **Reconstruction MAP needs a prior.** Planar-Laplace inversion under a uniform
  prior returns the observation itself (useless). The meaningful attack uses a
  prior — the road network (design §6.3 "decoding along the graph") or temporal
  smoothness — so reconstruction error can beat the injected noise mean
  (`2·unit_m/ε`). Decide the prior explicitly; network-snapping reuses the
  matcher and matches the design.
