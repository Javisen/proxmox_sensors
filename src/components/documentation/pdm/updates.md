**Datacenter Updates** reports the total number of updates in the last complete update snapshot accepted from PDM.

The sensor attributes organize the snapshot by remote and node and can include:

- the raw query status reported by PDM;
- the raw repository status;
- the number of updates;
- package/version information;
- oldest and newest refresh timestamps;
- the age of the oldest refresh;
- endpoint and complete-snapshot freshness.

Repository status values are shown as supplied by PDM and are not reinterpreted by the integration. No arbitrary stale threshold is applied to the refresh age.

An API error, incomplete payload, missing configured remote or non-success query state does not replace the previous complete snapshot with zero. The last valid snapshot is retained while the freshness attributes expose the degraded poll.

The exact upstream cache/refresh cadence is controlled by PDM and remains pending further upstream documentation; the integration polls the summary every 60 seconds without claiming that the underlying node data was refreshed at the same time.
