# 纸鹤展陈耐久研究簿 · SURVIVAL NOTES

分开灯带试件的失效事件与右删失，用 Kaplan–Meier 曲线、Greenwood区间和log-rank比较支持维护观察建议；并为维修后继续展出、会多次熄灭的灯带提供按试件重建工作区间的复发事件分析，用平均累计故障函数（MCF）与bootstrap同时置信带比较两批累计故障负担。

## 两条并行的证据线

本系统同时承载两类互不干扰的研究：

1. **终态耐久研究（旧口径，结果保持不变）**：每件只有一条终态观察，Kaplan–Meier + Greenwood log-log + 双侧 log-rank。
2. **复发故障研究（新增）**：可修复灯带的故障/修复/永久退出事件流，按**试件**为独立单位比较两批平均累计故障函数（MCF），并给出**同时置信带**。维修停机与永久退出后的时间不在险；断裂或退出后到达事件的试件整件隔离并保留原因。

两类研究各自建表、各自入队、各自的维护建议与获批导出；终态研究的算法版本、输入哈希与历史结果不受影响。

## 模拟场景

纸鹤展陈材料组有14位材料与维护研究员，跟踪两批24V柔性灯带。原流程把试验截止仍工作的试件也写成“寿命结束”，只比较平均时长，尾部在险试件数没有随图交付。上游为试件终态随访，本项目替代删失整理、耐久分布比较和建议复核段；下游为维护窗口讨论，不自动决定设备更换。应用不涉及医疗场景。

| 角色 | 页面与权限 | 典型动作 |
|---|---|---|
| admin / 材料负责人 | 六页读写、创建研究/建议、补备注、确认或退回 | 确认研究底稿适用范围 |
| analyst / 耐久研究员 | 六页阅读，创建研究/建议，补随访备注；不能确认 | 解释删失、在险表和比较结果 |
| viewer / 维护阅读者 | 六页只读，获批研究才能导出 | 查阅确认档案与CSV |

所有角色导出都必须有对应研究的获批建议。确认意味着研究证据允许归档，不是对灯带寿命或维护安全的保证。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
docker compose exec -T backend python -m scripts.seed_demo
```

[前端](http://localhost:18213)，[后端文档](http://localhost:19213/docs)。Nginx将`/api/`去掉后代理给FastAPI；直接后端调用不加该前缀。

| 邮箱 | 密码 | 角色 |
|---|---|---|
| admin@zhihe.demo | Zhihe2026! | admin |
| analyst@zhihe.demo | Zhihe2026! | analyst |
| viewer@zhihe.demo | Zhihe2026! | viewer |

Compose恰好frontend/backend/worker/db/redis五服务，全部健康检查。MySQL8、Redis7各使用命名卷，backend/worker共享JSON产物卷。backend等待数据库/Redis健康，frontend等待backend健康，worker每2秒写心跳。首次ORM metadata建表；迁移目录提供索引示例，已有表升级需审查迁移。

## 数据与一天的剧本

来源名`zh-lightstrip-followup.csv`，固定seed73/74生成两批各180件，共360个独立试件、360条终态随访。常规/改进工艺使用不同Weibull模拟时长，观察截止在900–1450小时，按25小时离散记录；128件右删失，比例35.56%。同一时点既有失效也有删失，用于真实并列风险集演示。每件只有一条终态观察，事件定义为光通量降到试验阈值，删失为截止仍工作。仅为合成数据。

复发事件来源名`zh-lightstrip-repair-events`（同360个试件的可修复事件流，约1600–1700条）。每个试件的故障(failure)/修复(repair)/永久退出(withdrawal)记录**按乱序到达**，以单调`received_seq`记录真实接收次序、`event_time`为自启用累计小时。常规批故障率高于改进批；每批固定2个隔离演示试件，分别覆盖`failure_while_down`、`event_after_withdrawal`、`withdrawal_while_working`、`repair_while_working`四种隔离原因。观察窗右端点默认1450小时。

seed按用户邮箱、批次code、试件code、随访specimen_id和基准研究名查重，只补缺失，不覆盖人工备注。启动`SEED_DEMO=true`自动seed；失败记录日志不阻塞服务。预置基准比较由真实算法计算，并有获批观察说明。

1. 09:00 江栩以analyst打开ZH-A和ZH-B，核对360件、小时单位及事件/删失含义。
2. 在“试件与随访”读取终态备注，补充一条仍工作试件的观察说明。
3. 创建“秋季两批封装耐久比较”，指定两批不同工艺、95%逐点置信水平。
4. worker从Redis队列独立执行KM、Greenwood log-log和两组log-rank。
5. 阅读两条曲线、删失短线、400/800/1200h在险表和中位是否已达到。
6. 检查并列事件表：同一时点先计全部在险，使用事件数更新，再移除该时点事件/删失。
7. 提交尾部观察和现场应力条件复核建议，不把p值作为工艺因果结论。
8. 阮青以admin确认或退回，并记录适用范围；重复确认409拒绝。
9. 林舟以viewer打开确认档案、导出KM表与SHA256，不能创建或审批。

## 算法口径

- **Kaplan–Meier**：每个唯一观察时点的风险集`n_i=count(duration>=t_i)`；事件数d_i、删失c_i。按`S(t)=Π(1-d_i/n_i)`递推，事件和删失同时发生时都先在风险集中。删失只减少后续风险集，不使曲线下降。
- **Greenwood log-log区间**：累计`G=Σ d_i/[n_i(n_i-d_i)]`，在`log(-log(S))`尺度用标准正态分位数和标准误`sqrt(G)/abs(log S)`构造逐点区间，再反变换，范围保持[0,1]。S=1明确[1,1]，S=0明确[0,0]，避免边界NaN。它不是整条曲线的同时置信带。
- **中位与在险**：仅当KM曲线首次达到≤0.5时报告对应小时；未达到为null/“尚未达到”，不拿最大时长或删失时长代替。400/800/1200h在险数为该时点之前仍在观察的试件数，观察时间正好等于时点也计入。
- **双侧log-rank**：汇总两组所有事件时点，`E_A=d*n_A/n`，`V=d*(n_A/n)*(n_B/n)*(n-d)/(n-1)`（n≤1则V=0），`χ²=(ΣO_A-ΣE_A)²/ΣV`，自由度1，p=`erfc(sqrt(χ²/2))`。并列事件的有限总体校正保留。无事件或ΣV≈0时`estimable=false`、χ²/p=null，不给伪显著性。
- 前提为独立试件、非信息性右删失；没有延迟入组、左/区间删失、重复事件、竞争风险或协变量调整。log-rank在比例风险差异下较敏感，交叉曲线可能检出力低；结果只作关联解释。
- 失败态：每组少于2件、时长≤0/非有限/>1e6小时、事件非布尔、重复试件、相同批次、置信水平越界明确拒绝。全删失是合法研究：平坦曲线、中位未达到、log-rank不可估；不是失败或无限寿命证明。
- 输入SHA256按试件code稳定排序，覆盖两组批次标识/工艺、所有试件字段、随访时长/状态/备注、置信水平、小时单位、在险时点与方法版本。保存结果含完整曲线、区间与事件风险集表，运行的参数保留在数据库。

官方参考：[SciPy ECDF与右删失KM](https://docs.scipy.org/doc/scipy-1.15.1/reference/generated/scipy.stats.ecdf.html)、[Greenwood区间](https://docs.scipy.org/doc/scipy-1.15.1/reference/generated/scipy.stats._result_classes.EmpiricalDistributionFunction.confidence_interval.html)、[log-rank口径](https://docs.scipy.org/doc/scipy-1.15.1/reference/generated/scipy.stats.logrank.html)。计算实现在本项目标准库算法中；SciPy1.15.1另作独立测试oracle，未用测试数值硬编码结果。

## 复发事件（可修复灯带 MCF）算法口径

只记首次故障会漏掉维修后再次熄灭的后续负担；把同一灯带的各次故障拆成独立试件又会人为增大样本量、低估不确定性。本系统因此以**试件**为独立单位处理复发事件。

- **乱序重建与工作区间**：事件按 `(event_time, received_seq)` 稳定排序恢复事件链，逐事件推进 `working → down → working/withdrawn` 状态机。故障时刻本身在险，工作区间在故障时刻闭合；修复把试件带回工作态，新工作区间从修复时刻起算；**维修停机与永久退出后的时间不在险**。观察窗结束仍在工作则补一段到右端点的右删失区间。
- **整件隔离**：出现断裂或退出后到达的事件时，该试件整件隔离，其在险历程不进入MCF；全部原始记录仍保留在事件链里供核对，并给出触发事件与原因代码。隔离原因含：`repair_while_working`（工作态收到无对应故障的修复）、`failure_while_down`（停机未修复又来故障）、`withdrawal_while_working`（工作态直接永久退出、链未闭合）、`event_after_withdrawal`（永久退出后仍有事件到达），以及未知类型、非正时间、超出观察窗等。隔离后每批有效试件少于2件则研究失败。
- **平均累计故障函数 MCF（Nelson 口径）**：事件时点增量 `ΔMCF = d(t)/n(t)`，`n(t)` 为该时刻处于工作区间内的试件数（bisect 覆盖计数，故障时刻计入），MCF 为累计阶梯，维修本身不使曲线上升。
- **不确定性以试件为单位**：逐点区间与同时置信带都基于**试件非参数 bootstrap**（默认1000次、固定seed，整件重抽样）。逐点区间取 bootstrap 分位数，自动容纳故障计数偏态；同时置信带取每条重抽样曲线相对观测曲线偏差的下/上确界分位数，覆盖率面向**整条曲线**而非单个时点。另附 Lawless–Nadeau（1995）计数过程稳健标准误（试件累计故障计数的样本方差/n）作描述量。
- **两批比较**：在两批故障时点并集网格上计算 `MCF(A)−MCF(B)`，给出逐点 bootstrap 区间、差值尺度上确界**同时置信带**，并标注带是否全程不含零；早期在险信息不足时差异可能要经过一段观察时间才建立，结论不外推到时间原点。
- 前提为试件间独立、同一试件内复发允许相关（由试件层面重抽样覆盖）、维修/退出过程非信息性。MCF 是描述累计故障负担的关联工具，不是寿命预测，也不自动决定维修周期。
- 输入SHA256按试件code稳定排序，覆盖两批全部乱序事件、观察窗右端点、置信水平、bootstrap seed与方法版本。结果含两批MCF曲线/逐点区间/同时带、差值带、每个有效试件的事件链与工作区间（在险历程）、隔离试件清单与原因。方法版本 `mcf-bootstrap-supremum-v1`。Monte Carlo 校准（n=40、400次重抽样、150轮）显示单组同时带覆盖约94%、差值同时带覆盖零约93%，符合95%名义水平。

## 页面与工程

导航为八个入口：研究总览、试件与随访（终态/复发两个视图）、比较配置、耐久结果、复发研究配置、累计故障结果、维护建议、研究留痕。TestCohort/Specimen/FollowupEvent/SurvivalRun/MaintenanceNote 贯穿终态线；RepairEvent/RecurrentRun 贯穿复发线，两条线共用 Cohort/Specimen/User/Audit。User/Audit为横切实体。

| 部分 | 技术 |
|---|---|
| 后端 | Python3.11 / FastAPI / SQLAlchemy / 标准库统计（MCF bootstrap 仅用标准库 random/bisect） |
| 前端 | Vue3 / TypeScript / Pinia / Vue Router / Vite6.4.6 |
| 数据 | MySQL8 / Redis7 AOF |
| UI | 修复档案米黄纸、古铜和深灰曲线；Noto Serif SC + Noto Sans SC |

```
backend/src/{models,schemas,services,controllers,routes,middlewares,utils,constants,config}
backend/src/{main.py,worker.py}
backend/scripts/seed_demo.py
backend/migrations/001_initial.sql 002_recurrent_events.sql
frontend/src/{api,stores,types,components,hooks,pages,router,utils,constants}
```

终态线复用 RunSummary/SurvivalPlot/RiskTable；复发线使用 RecurrentRunSummary/McfPlot/McfDifferencePlot/EventChainInspector/RepairEventFlow，DataTable/StatusBadge/Notice、useAction/useResearchData 两线共用。worker 单进程非阻塞轮询 `survival:jobs` 与 `recurrent:jobs` 两个 Redis 队列，复发任务不阻塞终态任务；`main()` 加 `__main__` 守卫以便单测导入。角色枚举`backend/src/constants/roles.py`、运行枚举`status.py`，对应`frontend/src/constants/enums.ts`。JWT8小时，PBKDF2-SHA256，权限每次查数据库。审计覆盖登录、随访备注、两类任务、两类建议和确认；全局错误与登录限流为两个独立中间件。复发研究的获批导出为单CSV多区块（MCF曲线/同时带、差值带、在险历程、隔离清单），与终态导出相互独立。

## 配置与本地开发

| 变量 | 默认 | 用途 |
|---|---|---|
| COMPOSE_PROJECT_NAME | survival-notes | 命名空间 |
| FRONTEND_PORT | 18213 | 前端 |
| BACKEND_PORT | 19213 | API |
| DB_PORT | 17713 | MySQL宿主映射 |
| JWT_SECRET | local-survival-notes-change-this-key | 本地演示密钥，部署前更换 |
| SEED_DEMO | true | 启动seed |
| ARTIFACTS_DIR | /artifacts | worker JSON产物与心跳目录（本地开发可重定向） |

Python3.11安装backend/requirements.txt，设置DATABASE_URL/REDIS_URL；`cd backend && uvicorn src.main:app --reload`，另起`python -m src.worker`。前端`npm install && npm run dev`，本地为`/api`设置后端代理。正式演示以Compose为准。

```bash
docker compose down -v --remove-orphans
```

外置真实测试、截图与TESTING位于`../../test-artifacts/gb-0009/`。源码不放截图、日志或测试报告；.env及缓存不提交。

## 已知边界

合成冻结数据，无仪器/文件上传；仅允许补随访备注，不编辑终态时长/状态，复发事件流同样为只读核对（乱序由seed模拟，前端不提供手工录入）。单worker无running自动恢复、事务outbox、多实例锁；中断任务需重提。登录限流仅进程内。终态线未给中位置信区间、RMST、风险比或比例风险检验；复发线未做协变量调整、竞争风险或含随机效应的参数复发模型，bootstrap为固定1000次非参数重抽样，不自动推荐更换时间。ORM metadata初建表不等于完整迁移链，已有库用`migrations/002_recurrent_events.sql`升级；字体依赖网络，离线回退。

## License

MIT，见LICENSE。
