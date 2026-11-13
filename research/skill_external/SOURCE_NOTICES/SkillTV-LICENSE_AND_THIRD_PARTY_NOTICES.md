# License and third-party notices

## Project licenses

The authors' original software and documentation are licensed under the Apache
License 2.0 in `LICENSE`.

The authors' original benchmark data are licensed under Creative Commons
Attribution 4.0 International as described in `DATA_LICENSE.md`.

These licenses apply only where the SkillTV-Bench Authors have the legal right
to grant them. They do not replace third-party terms.

## Third-party materials

Third-party files remain subject to their original licenses and notices, not
to any future license selected for the authors' original contributions.
License files distributed with individual task skills are retained next to
those skills under:

```text
data/**/environment/available_skills/**/LICENSE*
data/**/environment/available_skills/**/licenses/*
```

In particular:

- source trajectories were selected from the archived
  [`xiangyi-completed/withskills-claude-code`](https://github.com/benchflow-ai/skillsbench-trajectories/tree/main/xiangyi-completed/withskills-claude-code)
  collection in `benchflow-ai/skillsbench-trajectories`, whose upstream
  repository is licensed under the GNU Affero General Public License version
  3.0 ([license text](https://github.com/benchflow-ai/skillsbench-trajectories/blob/main/LICENSE));
- the SeisBench license retained with the earthquake phase-association skills
  is the GNU General Public License version 3 from the official SeisBench
  distribution;
- the ObsPy license retained in the same task directory contains its upstream
  GPL/LGPL terms; and
- document-processing skills retain their adjacent license files.

Task instructions, trajectories, and artifacts may also refer to external
software, models, publications, or datasets. Such references do not change the
licenses of those external works. Consult adjacent notices and upstream
projects for reuse terms.

## Credentials and services

No API credentials or private service configuration are included. Users must
supply their own authorized credentials for optional model and agent services.
