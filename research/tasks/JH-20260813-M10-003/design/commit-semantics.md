# M10-003 commit semantics

`baseline.git_head` is the **execution content base**, not the commit that
later records the task packet or mailbox notification.  For M10-003 it is
`f62c31cfe2ad1333175a877d9b4018eead1db6b2`, the commit that completed the
Codex-owned minimal authority sync before this task was issued.

For clarity about the superseded packet:

| Commit | Meaning | Not the execution base because |
|---|---|---|
| `532b209` | M9 closure state observed while the first M10 draft was designed | it predates M10 packet creation and the authority sync |
| `c91fad9` | commit that recorded the first M10 packet | it is a task-packet commit, not the repository content baseline mentioned by its request |
| `8d6e341` | mailbox notification that M10-002 was ready | mailbox is notification only, not task authority or a code/data base |
| `f62c31c` | Codex authority-sync commit | M10-003 execution base |

The later M10-003 packet commit is a transport/contract coordinate. Claude
must use the signed request plus its recorded `baseline.git_head` and baseline
snapshots; it must not infer an alternative execution base from mailbox text.
