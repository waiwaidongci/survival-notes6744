<script setup lang="ts">
import {RecurrentRun} from '../types/domain';
import {number} from '../utils/format';
const props=defineProps<{run:RecurrentRun}>();
const endMcf=(i:number)=>{const c=props.run.result.groups[i].curve;return c.length?c[c.length-1].mcf:0;};
</script>
<template>
  <div class="run-summary recurrent-summary">
    <div v-for="(g,i) in run.result.groups" :key="g.cohort.id" :class="['group-summary','group-'+i]">
      <span>{{g.cohort.code}} / {{g.cohort.process}}</span>
      <h3>{{g.cohort.name}}</h3>
      <b>{{number(endMcf(i),3)}}</b>
      <small>观察窗末端 MCF · {{g.n_failures}} 次故障 / {{g.specimen_valid}} 有效试件
        <template v-if="g.specimen_quarantined"> · {{g.specimen_quarantined}} 件隔离</template>
      </small>
    </div>
    <div class="test-summary">
      <span>BOOTSTRAP / 试件重抽样</span>
      <b>{{run.result.bootstrap_resamples}}</b>
      <small>在险 {{number(run.result.groups.reduce((s,g)=>s+g.total_exposure_hours,0),0)}} 小时 · 置信水平 {{Math.round(run.confidence*100)}}%</small>
    </div>
  </div>
</template>
