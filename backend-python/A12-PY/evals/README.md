# AI 教学引擎离线评测

`golden_teaching_cases.jsonl` 覆盖小学、初中、高中、中职和无障碍教学场景。评测脚本不消耗模型额度，固定检查页数、教学目标、互动设计、质量评分和降级透明度，适合放入 CI 做基础回归。

```powershell
.venv\Scripts\python.exe evals\run_offline_evals.py
```

线上评测应在有模型额度的环境补充：语义一致性、事实正确性、引用命中率、教师采纳率和生成耗时。运行数据会写入 `a12_ai_run_log`，教师修改/采纳数据写入 `a12_ai_feedback`。

真实模型基准测试：

```powershell
# 模型探针、向量检索 Top-1、大纲质量
.venv\Scripts\python.exe evals\run_ai_benchmarks.py

# 额外运行 8 页 PPT 串行与 8 并发对比（会产生实际模型费用）
.venv\Scripts\python.exe evals\run_ai_benchmarks.py --full
```

报告输出到 `evals/results/benchmark_latest.json` 和 `benchmark_latest.md`。只有模型真实返回且全部页面未降级时，脚本才计算性能结论。
