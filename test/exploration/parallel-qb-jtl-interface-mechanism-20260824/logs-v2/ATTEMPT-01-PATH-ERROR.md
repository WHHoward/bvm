# v2 batch attempt 01 — output-directory path error

该尝试在 shell output redirection 阶段失败，没有启动 JoSIM，也没有生成
raw scientific data。

- `logs-v2/<fixture>/` 子目录尚未创建；
- shell 无法打开 stdout/exitcode 路径，exit `1`；
- 修正为每个 fixture 独立的 `raw-v2/<fixture>/` 和 `logs-v2/<fixture>/` 后，
  重新执行了同一 preregistered point；
- 最终有效 jobs 见 `logs-v2/<fixture>/exitcode`，均为 `0`。

该 attempt 不属于 physical failure。
