"""Import every first-party implementation so its ``@register`` decorator runs.

The registry only knows a class once its defining module has been imported; the
orchestrator addresses implementations by name, so this module is the single place
that pulls them all in. Importing it is the registration side effect.
"""

from trajguard.attacks import attribute, membership, reconstruction, reidentification
from trajguard.datasets import geolife, ldptrace_dat
from trajguard.evaluation import metrics
from trajguard.maps import osm
from trajguard.matching import leuven
from trajguard.privacy import geoind, naive, none, point_ldp
from trajguard.synthesis import ldptrace, markov, rn_ldp_synth

# Referencing the modules keeps linters happy; importing them did the registration.
_IMPLEMENTATIONS = (
    reidentification,
    membership,
    reconstruction,
    attribute,
    geolife,
    ldptrace_dat,
    metrics,
    osm,
    leuven,
    none,
    geoind,
    point_ldp,
    naive,
    markov,
    rn_ldp_synth,
    ldptrace,
)
