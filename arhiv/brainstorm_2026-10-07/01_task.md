# Brainstorm task: new protection mechanisms (user-level pure LDP, road-network trajectory synthesis)

## Research gap
We need NEW protection mechanisms for a doctoral project. The gap: synthesis of
road-network-constrained trajectories (complete paths on a road graph WITH a time
component: departure time and per-segment timing/speeds), such that the released
synthetic data satisfies **user-level local differential privacy (LDP)**. The unit of
protection is the whole user (all trajectories they contributed in a collection
window), not a point, a segment or a single trajectory.

- **Pure LDP is mandatory**: every user randomizes on their own device; the server is
  untrusted. No trusted shuffler and no secure aggregation in the core design (they may
  be mentioned only as optional extensions).
- A user may collect data for e.g. one month, then submit ONE randomized report. A later
  submission counts as a new user (a new privacy unit). The server aggregates reports and
  may update its model incrementally.
- Nothing forces the design to be "noisy parameters sent to the server"; any
  architecture that yields user-level pure LDP is in scope. The default sketch is:
  compute locally -> randomize -> aggregate server-side -> synthesize.

## Novelty requirement
The mechanism must not exist in published literature and must differ enough from
existing work to count as a contribution. Known neighbours (do not re-propose them):
LDPTrace, PrivTrace, AdaTrace, DPT, DP-Star, RetraSyn, Cunningham et al. (n-gram LDP with
external knowledge), trajectory-collection LDP methods (TrajLDP-style direction/segment
perturbation), DP-FedAvg-style federated models, and non-private road-network generators
(TS-TrajGen, Diff-RNTraj, DiffTraj, ControlTraj). Combining two known pieces is fine ONLY
if the combination solves a problem neither solves; say which.

## Scale constraint (important)
The benchmark has Geolife with 182 users (only ~809 map-matched train trajectories at
full scale). A larger Beijing taxi dataset (T-Drive, ~10,000 taxis, same road graph)
could be added later. With pure LDP, estimation error scales like 1/(eps*sqrt(n)): at
eps=1 and n=182 the standard deviation of a per-item frequency estimate (fraction of
users) is about 0.14 with OUE, so per-segment histograms are unusable and
segment-to-segment transition matrices are hopeless. Every idea must state explicitly:
what it can estimate meaningfully at n~180, what needs n~10,000, and its degradation
strategy for n~180 (lower-dimensional parameters, public priors from the road graph and
OSM road classes, hierarchical coarsening, ...).

## Benchmark facts
Read `.brainstorm/00_briefing.md` (about 950 words) in the repo root. Read ONLY that
file. Do not open anything else in the repo and do not look at the existing
`rn_ldp_synth` code: it is a prototype that does not work well and must NOT be used as a
template. Key points: the membership-inference attack calls only `fit` and
`sequence_log_prob(edge_seq)`; synthetic output is a sequence of road-graph edge ids
(timestamps would be new work); the benchmark synthesizes unlinked trajectories (no
synthetic user ids needed); time-aware synthetic utility metrics would be new work.

## Your output
Propose 3-4 DISTINCT mechanism ideas from your assigned lens. For each idea use EXACTLY
this template (150-300 words per idea, English, precise, no marketing):

### Idea <n>: <short name>
- **One-sentence pitch:**
- **What each user computes locally** (from their own trajectories; name the parameter
  vector and its dimension as a function of road-graph size, number of zones, etc.):
- **What is randomized and how** (the LDP primitive: randomized response, OUE/OLH,
  Laplace or piecewise mechanism for bounded numeric values, padding-and-sampling for
  set-valued data, sampling one item per user, ...; how the per-user sensitivity is
  bounded so the guarantee is user-level; budget split across components):
- **What the server does** (aggregation, debiasing, post-processing with road-graph
  constraints, model fitting):
- **How a synthetic trajectory is generated** (path on the road graph + departure time
  + per-segment timing):
- **Why it is user-level pure LDP** (two or three sentences; where the proof is easy and
  where it is subtle):
- **Expected behaviour at n~180 vs n~10,000** and the degradation strategy:
- **Closest existing work and what differs** (name papers/methods you know; be honest if
  you suspect the idea already exists):
- **Implementation effort** in a Python research codebase (S/M/L and main components):
- **Main risk / failure mode:**

Rules: prefer ideas whose privacy argument is clean (bounded per-user contribution,
standard LDP primitives, composition stated). No design may rely on a trusted party. The
time component is mandatory (at least departure time and plausible per-segment travel
times). Say what makes the output road-valid by construction (the road graph is public).
Distinctness and clarity beat quantity. You may run at most 3 web searches to check
whether a specific idea already exists; do not do a literature survey. End with a 5-line
"Ranking" saying which of your ideas is best and why.

Write the full output to the file named in your instructions. Then reply with ONLY: the
idea names, one line (max 25 words) each, and one line naming your top pick. Nothing else.
