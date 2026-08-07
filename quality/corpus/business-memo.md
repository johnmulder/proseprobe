# Database maintenance memo

The database restructuring moves two indexes to the reporting tablespace. It
does not change staffing, budgets, or team ownership.

Engineering and operations agreed to begin at 02:00 UTC. “Agreement” here means
both teams approved the same start time and rollback condition.

Memory alignment remains 64 bytes for the binary record format. This technical
use of alignment does not describe organizational consensus.

The migration has three checks: available disk space, replication lag, and a
verified backup. Each check maps to a recorded command result.

If replication lag exceeds five seconds, the operator will stop the migration
and restore the original indexes.
