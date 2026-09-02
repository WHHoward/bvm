# T100 failed attempt 01

这是一次被保留的执行失败记录，不是物理结果，也没有覆盖后续有效 raw。

- command: `./build/josim-cli -o test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T100/raw.csv test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/runs/T100/deck.cir`
- exit_code: `255`
- raw_created: `false`
- failure_class: `deck/include packaging error`
- reason: frozen relative `.include` depth was evaluated from the `runs/T100` directory and resolved into the wrong repository path.
- preserved_log: `runs/T100/run.log`
- corrective_action: valid decks were materialized under `migrated/`, at the fixture depth expected by the frozen include paths; no circuit physics was changed.
