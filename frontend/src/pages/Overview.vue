<script setup lang="ts">
import {computed} from 'vue';
import {ArrowUpRight, Plus, Repeat} from 'lucide-vue-next';
import {useResearchData} from '../hooks/useResearch';
import {useAuth} from '../stores/auth';
import RunSummary from '../components/RunSummary.vue';
import RecurrentRunSummary from '../components/RecurrentRunSummary.vue';
import SurvivalPlot from '../components/SurvivalPlot.vue';
import McfPlot from '../components/McfPlot.vue';
import Notice from '../components/common/Notice.vue';
import {percent} from '../utils/format';

const s=useResearchData(),auth=useAuth();
const run=computed(()=>s.runs.find(r=>r.status==='completed'));
const recRun=computed(()=>s.recurrentRuns.find(r=>r.status==='completed'));
const n=computed(()=>s.cohorts.reduce((sum,c)=>sum+c.specimen_count,0));
const censored=computed(()=>s.cohorts.reduce((sum,c)=>sum+c.censored,0));
const quarantined=computed(()=>recRun.value?recRun.value.result.groups.reduce((t,g)=>t+g.specimen_quarantined,0):0);
const totalFailures=computed(()=>recRun.value?recRun.value.result.groups.reduce((t,g)=>t+g.n_failures,0):0);
</script>
<template>
  <div class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow">RESEARCH DESK / 01</p>
        <h1>研究总览<span>终态耐久分布与可修复复发故障负担，两套证据并列。</span></h1>
      </div>
      <RouterLink v-if="auth.user?.role!=='viewer'" class="outline" to="/configure"><Plus :size="16"/>建立比较</RouterLink>
    </div>
    <Notice :message="s.error" @retry="s.refresh"/>

    <div class="overview-grid">
      <section class="evidence-sheet">
        <div class="section-top">
          <span class="eyebrow">LATEST TERMINAL / 最新终态研究</span>
          <RouterLink to="/results">阅读结果 <ArrowUpRight :size="14"/></RouterLink>
        </div>
        <template v-if="run">
          <RunSummary :run="run"/>
          <SurvivalPlot :result="run.result"/>
        </template>
        <p v-else class="empty">尚无终态研究，先选择两批工艺建立比较。</p>
      </section>
      <aside class="archive-note">
        <span class="eyebrow">READING NOTE / 001</span>
        <h2>没有观察到失效，<br/>并不意味着<br/>永不失效。</h2>
        <p>删失保留“至少已工作这么久”的信息。尾部在险试件少时，曲线与中位时间都要谨慎解释。</p>
        <div class="note-divider"/>
        <div class="count"><b>{{n}}</b><span>独立灯带试件<br/>{{n?percent(censored/n):'—'}} 右删失</span></div>
        <RouterLink to="/cohorts">打开试件档案 →</RouterLink>
      </aside>
    </div>

    <div class="recurrent-desk">
      <div class="section-top">
        <span class="eyebrow"><Repeat :size="12"/> LATEST RECURRENT / 最新复发故障研究（MCF）</span>
        <RouterLink to="/recurrent-results">阅读累计故障结果 <ArrowUpRight :size="14"/></RouterLink>
      </div>
      <template v-if="recRun">
        <RecurrentRunSummary :run="recRun"/>
        <McfPlot :result="recRun.result"/>
        <p class="caption">
          共 {{totalFailures}} 次复发故障；{{quarantined}} 个试件因事件链断裂或退出后到达事件被整件隔离，
          维修停机时间不计在险。<RouterLink class="text-link" to="/recurrent-configure">建立新的复发研究 →</RouterLink>
        </p>
      </template>
      <p v-else class="empty">尚无复发研究。维修后继续展出的灯带会多次熄灭，可在复发研究配置中按试件比较平均累计故障函数。</p>
    </div>

    <div class="section-heading"><h2>两批封装工艺</h2><span>zh-lightstrip-followup.csv</span></div>
    <div class="cohort-row">
      <RouterLink v-for="c in s.cohorts" :key="c.id" :to="'/cohorts?cohort='+c.id">
        <span class="eyebrow">{{c.code}} / {{c.process}}</span>
        <h3>{{c.name}}</h3>
        <p>{{c.specimen_count}} 件 · {{c.events}} 终态失效 · {{c.censored}} 右删失</p>
        <span>查阅随访与复发事件流 →</span>
      </RouterLink>
    </div>
  </div>
</template>
