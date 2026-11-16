<script setup lang="ts">
import {computed, ref} from 'vue';
import {useRoute} from 'vue-router';
import {useResearchData} from '../hooks/useResearch';
import RecurrentRunSummary from '../components/RecurrentRunSummary.vue';
import McfPlot from '../components/McfPlot.vue';
import McfDifferencePlot from '../components/McfDifferencePlot.vue';
import EventChainInspector from '../components/EventChainInspector.vue';
import StatusBadge from '../components/common/StatusBadge.vue';
import Notice from '../components/common/Notice.vue';
import {number} from '../utils/format';

const s=useResearchData(true),route=useRoute();
const selected=ref(Number(route.query.run)||0);
const activeCohort=ref(0);
const run=computed(()=>s.recurrentRuns.find(r=>r.id===selected.value)||s.recurrentRuns[0]);
const group=computed(()=>run.value?.result.groups[activeCohort.value]);
</script>
<template>
  <div class="page results-page recurrent-results">
    <div class="page-title">
      <div>
        <p class="eyebrow">RECURRENT EVIDENCE / 08</p>
        <h1>累计故障结果<span>同时阅读 MCF 曲线、同时置信带、事件链与在险历程。</span></h1>
      </div>
      <RouterLink class="outline" :to="'/notes'+(run?'?recurrent='+run.id:'')">记录维护建议 →</RouterLink>
    </div>
    <Notice :message="s.error" @retry="s.refresh"/>
    <div class="run-picker">
      <label>复发研究档案
        <select aria-label="复发研究档案" :value="run?.id||''"
          @change="selected=Number(($event.target as HTMLSelectElement).value)">
          <option v-for="r in s.recurrentRuns" :key="r.id" :value="r.id">#{{r.id}} / {{r.name}} / {{r.status}}</option>
        </select>
      </label>
      <StatusBadge v-if="run" :status="run.status"/>
    </div>

    <template v-if="run?.status==='completed'">
      <RecurrentRunSummary :run="run"/>
      <McfPlot :result="run.result"/>
      <McfDifferencePlot :diff="run.result.difference" :cutoff="run.result.cutoff_hours"/>

      <div class="comparison-note">
        <span>MCF 差值 A−B</span>
        <p>{{run.result.interpretation}}</p>
        <b>带全程含零：{{run.result.difference.excludes_zero_everywhere?'否（支持稳定差异）':'是'}}</b>
      </div>
      <p class="caption">{{run.result.assumptions}}</p>

      <div class="section-heading">
        <h2>事件链 · 隔离原因 · 在险历程核对</h2>
        <span>维修期间不在险，断裂/退出后到达事件整件隔离</span>
      </div>
      <div class="cohort-switch">
        <button v-for="(g,i) in run.result.groups" :key="g.cohort.id"
          :class="{active:activeCohort===i}" @click="activeCohort=i">
          {{g.cohort.code}} · {{g.cohort.name}}
          <small v-if="g.specimen_quarantined" class="quarantine-count">{{g.specimen_quarantined}} 隔离</small>
        </button>
      </div>
      <EventChainInspector v-if="group" :group="group"/>

      <div class="section-heading"><h2>MCF 曲线数值（前 12 个事件时点）</h2><span>逐点bootstrap区间</span></div>
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>批次</th><th>时间 / h</th><th>在险</th><th>事件</th><th>MCF</th><th>逐点下限</th><th>逐点上限</th><th>稳健SE</th></tr></thead>
          <tbody>
            <template v-for="(g,i) in run.result.groups" :key="g.cohort.id">
              <tr v-for="p in g.curve.slice(1,13)" :key="g.cohort.id+'-'+p.time">
                <td>{{g.cohort.code}}</td><td class="mono">{{number(p.time,1)}}</td>
                <td>{{p.at_risk}}</td><td>{{p.events}}</td>
                <td>{{number(p.mcf,4)}}</td><td>{{number(p.lower,4)}}</td>
                <td>{{number(p.upper,4)}}</td><td>{{number(p.se,4)}}</td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <p class="fingerprint">输入 SHA256 {{run.result.input_hash}} · 方法 {{run.result.method_version}} · bootstrap seed {{run.result.difference.seed}}</p>
    </template>
    <div v-else-if="run" class="pending">
      <h2>{{run.status==='failed'?'复发研究未能完成':'后台正在重建事件链并计算 MCF 与同时带'}}</h2>
      <p>{{run.error||'独立 worker 按试件重抽样执行 bootstrap，本页每2秒更新。'}}</p>
    </div>
    <p v-else class="empty">尚无复发研究，请先在复发研究配置中选择两批工艺创建比较。</p>
  </div>
</template>
