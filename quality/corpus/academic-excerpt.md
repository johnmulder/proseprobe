# Storage experiment

We measured write latency for 24 drives under the same temperature and queue
depth. The median fell from 8.4 milliseconds to 6.1 milliseconds after the
firmware update.

Smith (2020) argues that queue depth affects tail latency. Patel (2021) reports
the same association for rotational disks, but neither study tested this
firmware.

The samples were stored at 20 °C before each run. This passive construction
describes the procedure without concealing who made a policy decision.

The result may be useful for operators with similar hardware, although the
small sample does not support a claim about every drive model.

This experiment does not fill a gap in all storage research. It tests one
version on one hardware configuration.
