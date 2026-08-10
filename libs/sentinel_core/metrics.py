"""Prometheus metrics.

Naming follows Prometheus conventions: ``_total`` for counters, base units in
the metric name (seconds, not milliseconds), and low-cardinality labels only.

Cardinality warning worth remembering: labelling by ``monitor_id`` is safe here
because a portfolio deployment has tens of monitors. Labelling by URL or by
customer id is how teams accidentally melt their Prometheus.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ---- Probe outcomes (written by the worker) ----

PROBES_TOTAL = Counter(
    "sentinel_probes_total",
    "Total probes executed, partitioned by outcome.",
    labelnames=("monitor_id", "outcome"),  # outcome: up | down
)

PROBE_DURATION_SECONDS = Histogram(
    "sentinel_probe_duration_seconds",
    "Wall-clock duration of an outbound probe request.",
    labelnames=("monitor_id",),
    # Buckets tuned for HTTP checks: 10ms up to 10s.
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

PROBE_UP = Gauge(
    "sentinel_monitor_up",
    "Most recent probe result: 1 if up, 0 if down.",
    labelnames=("monitor_id",),
)

# ---- Scheduler ----

CHECKS_ENQUEUED_TOTAL = Counter(
    "sentinel_checks_enqueued_total",
    "Probe jobs pushed onto the queue by the scheduler.",
)

SCHEDULER_LOOP_SECONDS = Histogram(
    "sentinel_scheduler_loop_duration_seconds",
    "Time spent in one scheduler tick.",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

# ---- Queue (the HPA signal) ----

QUEUE_DEPTH = Gauge(
    "sentinel_queue_depth",
    "Number of probe jobs waiting in Redis.",
)
